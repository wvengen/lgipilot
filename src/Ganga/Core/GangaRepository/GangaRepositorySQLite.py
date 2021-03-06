# Note: Following stuff must be considered in a GangaRepository:
#
# * lazy loading
# * locking

from GangaRepository import GangaRepository, PluginManagerError, EmptyGangaObject, RepositoryError, InaccessibleObjectError
from Ganga.Utility.Config import getConfig
import os, os.path, fcntl, time, errno

import sqlite

try:
         import cPickle as pickle
except:
         import pickle

import Ganga.Utility.logging
logger = Ganga.Utility.logging.getLogger()

from Ganga.GPIDev.Lib.GangaList.GangaList import makeGangaListByRef
from Ganga.GPIDev.Base.Objects import Node

class GangaRepositorySQLite(GangaRepository):
    """GangaRepository SQLite"""

    def startup(self):
        """ Starts an repository and reads in a directory structure."""
        self._load_timestamp = {}
        self._cache_load_timestamp = {}
        self.known_bad_ids = []
        self.root = os.path.join(self.registry.location,"0.1",self.registry.name)
        try:
            os.makedirs(self.root)
        except OSError, x:
            pass
        self.con = sqlite.connect(os.path.join(self.root,"database.db"))
        print "Connected to ", os.path.join(self.root,"database.db")
        self.cur = self.con.cursor()
        tables = self.cur.execute("SELECT name FROM sqlite_master WHERE type='table' and name LIKE 'objects'")
        if len(self.cur.fetchall()) == 0:
            self.cur.execute("CREATE TABLE objects (id INTEGER PRIMARY KEY, classname VARCHAR(30), category VARCHAR(20), idx VARCHAR(100), data VARCHAR(1000))")
        self.con.commit()
        self.update_index(verbose = True)

    def shutdown(self):
        """Shutdown the repository. Flushing is done by the Registry
        Raise RepositoryError"""
        self.cur.close()
        self.con.close()

    def update_index(self,id = None,verbose=False):
        """ Update the list of available objects
        Raise RepositoryError"""
        # First locate and load the index files
        logger.debug("updating index...")
        self.cur.execute("SELECT id,classname,category,idx FROM objects")
        for e in self.cur:
            id = int(e[0])
            if e[1] is None: # deleted object
                continue
            # Locked IDs can be ignored
            #if id in self.sessionlock.locked:
            #    continue
            # Now we treat unlocked IDs
            if id in self.objects:
                obj = self.objects[id]
            else:
                obj = self._make_empty_object_(id,e[2],e[1])
            obj._index_cache = pickle.loads(e[3])
        logger.debug("updated index done")

    def add(self, objs, force_ids = None):
        """ Add the given objects to the repository, forcing the IDs if told to.
        Raise RepositoryError"""
        ids = []
        if not force_ids is None: # assume the ids are already locked by Registry
            if not len(objs) == len(force_ids):
                raise RepositoryError(self, "Internal Error: add with different number of objects and force_ids!")
            ids = force_ids
        for i in range(0,len(objs)):
            cls = objs[i]._name
            cat = objs[i]._category
            objs[i]._index_cache = self.registry.getIndexCache(objs[i])
            data = pickle.dumps(objs[i]._data).replace("'","''")
            idx = pickle.dumps(objs[i]._index_cache).replace("'","''")
            if force_ids is None:
                self.cur.execute("INSERT INTO objects (id,classname,category,idx,data) VALUES (NULL,'%s','%s','%s','%s')" % (cls,cat,idx,data))
            else:
                self.cur.execute("INSERT INTO objects (id,classname,category,idx,data) VALUES (%i,'%s','%s','%s','%s')" % (force_ids[i],cls,cat,idx,data))
            ids.append(self.cur.lastrowid)
            self._internal_setitem__(ids[i], objs[i])
        self.con.commit()
        return ids

    def flush(self, ids):
        for id in ids:
            obj = self.objects[id] 
            if obj._name != "EmptyGangaObject":
                obj._index_cache = self.registry.getIndexCache(obj)
                data = pickle.dumps(obj._data).replace("'","''")
                idx = pickle.dumps(obj._index_cache).replace("'","''")
                self.cur.execute("UPDATE objects SET idx='%s',data='%s' WHERE id=%s" % (idx, data, id))
                #print "flushing id ", id, " backend ", obj.backend._name
        self.con.commit()

    def load(self, ids):
        self.cur.execute("SELECT id,classname,category,data FROM objects WHERE id IN (%s)" % (",".join(map(str,ids))))
        for e in self.cur:
            #print "load: ",e
            id = int(e[0])
            if e[1] is None: # deleted object
                continue
            if not id in self.objects:
                obj = self._make_empty_object_(id,e[2],e[1])
            else:
                obj = self.objects[id]
            if obj._data is None:
                obj._data = pickle.loads(e[3])
                obj.__setstate__(obj.__dict__)
            ids.remove(id)
        if len(ids) > 0:
            raise KeyError(ids[0])

    def delete(self, ids):
        for id in ids:
            self.cur.execute("UPDATE objects SET classname=NULL,category=NULL,idx=NULL,data=NULL WHERE id=%s" % (id))
            self._internal_del__(id)
        self.con.commit()

    def lock(self,ids):
        return ids

    def unlock(self,ids):
        return ids

    def get_lock_session(self,id):
        """get_lock_session(id)
        Tries to determine the session that holds the lock on id for information purposes, and return an informative string.
        Returns None on failure
        """
        return ""

    def get_other_sessions(self): 
        """get_session_list()
        Tries to determine the other sessions that are active and returns an informative string for each of them.
        """
        return []

    def reap_locks(self):
        """reap_locks() --> True/False
        Remotely clear all foreign locks from the session.
        WARNING: This is not nice.
        Returns True on success, False on error."""
        return False

    def clean(self):
        """clean() --> True/False
        Clear EVERYTHING in this repository, counter, all jobs, etc.
        WARNING: This is not nice."""
        self.shutdown()
        os.unlink(os.path.join(self.root,"database.db"))
        self.startup()
        
