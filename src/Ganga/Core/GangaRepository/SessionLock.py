# This class (SessionLockManager) encapsulates fcntl-based locking that works on NFS, AFS and locally.
# You can use 
# python SessionLock.py {1|2}
# to run locking tests (run several instances in the same directory, from different machines)

import os, time, errno, threading, fcntl, random

import sys
if sys.hexversion >= 0x020600F0:
    Set = set
else:
    from sets import Set

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    from Ganga.Core.GangaThread import GangaThread
    from Ganga.Core.GangaRepository import RepositoryError
    import Ganga.Utility.logging
    logger = Ganga.Utility.logging.getLogger()
except ImportError:
    print "IMPORT ERROR SHOULD NOT OCCUR IN PRODUCTION CODE!!!!!!!!!!!!!!!!!!!!!!"
    from threading import Thread
    class GangaThread(Thread):
        def __init__(self,name):
            self.name = name
            super(GangaThread,self).__init__()
        def should_stop(self):
            return False

    class Logger:
        def warning(self,msg):
            print msg
        def debug(self,msg):
            print msg

    class RepositoryError(Exception):
        pass
    logger = Logger() 

session_expiration_timeout = 40 # seconds
session_lock_refresher = None

class SessionLockRefresher(GangaThread):
    def __init__(self,session_name,sdir,fn, repo):
        GangaThread.__init__(self, name='SessionLockRefresher', critical=False)
        self.session_name = session_name
        self.sdir = sdir
        self.fn = fn
        self.repos = [repo]
        

    def run(self):

        try:
            while not self.should_stop():
                ## TODO: Check for services active/inactive
                try:
                    try:
                        oldnow = os.stat(self.fn).st_ctime
                        os.utime(self.fn,None)
                        now = os.stat(self.fn).st_ctime
                        #if now - oldnow  > session_expiration_timeout/2:
                        #    logger.warning("%s: This session can only update its session file every %s seconds - this can cause problems with other sessions!" % (time.time(), now - oldnow))
                        #print "%s: Delta is %i seconds" % (time.time(), now - oldnow)
                    except OSError, x:
                        if x.errno != errno.ENOENT:
                            logger.debug("Session file timestamp could not be updated! Locks could be lost!")
                        else:
                            raise RepositoryError(self.repos[0], "Own session file not found! Possibly deleted by another ganga session.\n\
                                    Possible reasons could be that this computer has a very high load, or that the system clocks on computers running Ganga are not synchronized.\n\
                                    On computers with very high load and on network filesystems, try to avoid running concurrent ganga sessions for long.")
                    # Clear expired session files if monitoring is active

                    try:
                        from Ganga.Core import monitoring_component
                        if not monitoring_component is None and monitoring_component.enabled:
                            # Make list of sessions that are "alive"
                            ls_sdir = os.listdir(self.sdir)
                            session_files = [f for f in ls_sdir if f.endswith(".session")]
                            lock_files = [f for f in ls_sdir if f.endswith(".locks")]
                            for sf in session_files:
                                if os.path.join(self.sdir,sf) == self.fn:
                                    continue
                                mtm = os.stat(os.path.join(self.sdir,sf)).st_ctime
                                #print "%s: session %s delta is %s seconds" % (time.time(), sf, now - mtm)
                                if now - mtm  > session_expiration_timeout:
                                    logger.warning("Removing session %s because of inactivity (no update since %s seconds)" % (sf, now - mtm))
                                    os.unlink(os.path.join(self.sdir,sf))
                                    session_files.remove(sf)
                                #elif now - mtm  > session_expiration_timeout/2:
                                #    logger.warning("%s: Session %s is inactive (no update since %s seconds, removal after %s seconds)" % (time.time(), sf, now - mtm, session_expiration_timeout))
                            # remove all lock files that do not belong to sessions that are alive
                            for f in lock_files:
                                if not f.endswith(".session"):
                                    asf = f.split(".session")[0] + ".session"
                                    if not asf in session_files:
                                        logger.warning("Removing dead file %s" % (f))
                                        os.unlink(os.path.join(self.sdir,f))
                    except OSError, x:
                        # nothing really important, another process deleted the session before we did.
                        logger.info("Unimportant OSError in loop: %s" % x)
                except RepositoryError:
                    break
                except Exception, x:
                    logger.warning("Internal exception in session lock thread: %s %s" % (x.__class__.__name__, x))
                time.sleep(1+random.random())
        finally:
            # On shutdown remove session file
            try:
                logger.debug("Removing file %s" % (self.fn))
                os.unlink(self.fn)
            except OSError, x:
                logger.debug("Session file was deleted already or removal failed: %s" % (x))
            self.unregister()
            global session_lock_refresher
            session_lock_refresher = None

    def addRepo(self,repo):
        self.repos.append(repo)

class SessionLockManager(object):
    """ Class with thread that keeps a global lock file that synchronizes
    ID and counter access across Ganga sessions.
    DEVELOPER WARNING: On NFS, files that are not locked with lockf (NOT flock) will 
    NOT be synchronized across clients, even if a global lock file is used!
    Interface:
        * startup() starts the session, automatically called on init
        * shutdown() stops the thread, FREES ALL LOCKS
        * make_new_ids(n) returns n new (locked) ids
        * lock_ids(ids) returns the ids that were successfully locked
        * release_ids(ids) returns the ids that were successfully released (now: all)
    All access to an instance of this class MUST be synchronized!
    Should ONLY raise RepositoryError (if possibly-corrupting errors are found)
    """
    def mkdir(self,dn):
        """Make sure the given directory exists"""
        try:
            os.makedirs(dn)
        except OSError, x:
            if x.errno != errno.EEXIST:
                raise RepositoryError(self.repo, "OSError on directory create: %s" % x)

    def __init__(self, repo, root, name, minimum_count=0):

        self.repo = repo
        self.mkdir(root)
        realpath = os.path.realpath(root)
        # Use the hostname (os.uname()[1])  and the current time in ms to construct the session filename.
        # TODO: Perhaps put the username here?
        global session_lock_refresher
        if session_lock_refresher is None:
            session_name = ".".join([os.uname()[1],str(int(time.time()*1000)),str(os.getpid()),"session"])
        else:
            session_name = session_lock_refresher.session_name

        self.sdir = os.path.join(realpath,"sessions")
        self.gfn = os.path.join(self.sdir, session_name)
        self.fn = os.path.join(self.sdir, session_name+"."+name+".locks")
        self.cntfn = os.path.join(realpath,name,"cnt")

        self.afs = (realpath[:4] == "/afs")
        self.locked = Set()
        self.count = minimum_count
        self.session_name = session_name
        self.name = name
        self.realpath = realpath


    
    def startup(self):
        # Ensure directories exist
        self.mkdir(os.path.join(self.realpath,"sessions"))
        self.mkdir(os.path.join(self.realpath,self.name))

        # setup global lock
        self.global_lock_setup()
        self.global_lock_acquire()
        try:
            # setup counter file if it does not exist, read it if it does
            if not os.path.exists(self.cntfn):
                try:
                    fd = os.open(self.cntfn, os.O_EXCL | os.O_CREAT | os.O_WRONLY)
                    os.write(fd,"0")
                    os.close(fd)
                except OSError, x:
                    if x.errno != errno.EEXIST:
                        raise RepositoryError(self.repo, "OSError on count file create: %s" % x)
            try:
                self.count = max(self.count,self.cnt_read())
            except ValueError:
                logger.error("Corrupt count file '%s'! Trying to recover..." % (self.cntfn))
            except OSError, x:
                raise RepositoryError(self.repo, "OSError on count file '%s' access!" % (self.cntfn))
            self.cnt_write()
            # Setup session file
            try:
                fd = os.open(self.fn, os.O_EXCL | os.O_CREAT | os.O_WRONLY)
                os.write(fd,pickle.dumps(Set()))
                os.close(fd)
            except OSError, x:
                raise RepositoryError(self.repo, "Error on session file '%s' creation: %s" % (self.fn,x))
            global session_lock_refresher
            if session_lock_refresher is None:
                try:
                    os.close(os.open(self.gfn, os.O_EXCL | os.O_CREAT | os.O_WRONLY))    
                except OSError, x:
                    raise RepositoryError(self.repo, "Error on session file '%s' creation: %s" % (self.gfn,x))
                session_lock_refresher = SessionLockRefresher(self.session_name, self.sdir, self.gfn, self.repo)
                session_lock_refresher.start()
            else:
                session_lock_refresher.addRepo(self.repo)
            self.session_write()
        finally:
            self.global_lock_release()


    def shutdown(self):
        """Shutdown the thread and locking system (on ganga shutdown or repo error)"""
        self.locked = Set()
        try:
            logger.debug("Session file '%s' deleted " % (self.fn))
            os.unlink(self.fn)
        except OSError, x:
            logger.debug("Session file '%s' was deleted already or removal failed: %s" % (self.fn,x))

    # Global lock function
    def global_lock_setup(self):
        self.lockfn = os.path.join(self.sdir,"global_lock")
        try:
            file(self.lockfn,"w").close() # create file (does not interfere with existing sessions)
            self.lockfd = os.open(self.lockfn,os.O_RDWR)
        except IOError, x:
            raise RepositoryError(self.repo, "Could not create lock file '%s': %s" % (self.lockfn, x))
        except OSError, x:
            raise RepositoryError(self.repo, "Could not open lock file '%s': %s" % (self.lockfn, x))

    def global_lock_acquire(self):
        try:
            fcntl.lockf(self.lockfd,fcntl.LOCK_EX)
        except IOError, x:
            raise RepositoryError(self.repo, "IOError on lock ('%s'): %s" % (self.lockfn, x))
            
    def global_lock_release(self):
        try:
            fcntl.lockf(self.lockfd,fcntl.LOCK_UN)
        except IOError, x:
            raise RepositoryError(self.repo, "IOError on unlock ('%s'): %s" % (self.lockfn, x))

    # Session read-write functions
    def session_read(self,fn):
        """ Reads a session file and returns a set of IDs locked by that session.
            The global lock MUST be held for this function to work, although on NFS additional
            locking is done
            Raises RepositoryError if severe access problems occur (corruption otherwise!) """
        try:
            fd = os.open(fn, os.O_RDONLY) # This can fail (thats OK, file deleted in the meantime)
            try:
                if not self.afs: # additional locking for NFS
                    fcntl.lockf(fd,fcntl.LOCK_SH)
                try:
                    return pickle.loads(os.read(fd,104857600)) # read up to 100 MB (that is more than enough...)
                except Exception, x:
                    logger.warning("corrupt or inaccessible session file '%s' - ignoring it (Exception %s %s)."% (fn, x.__class__.__name__, x))
            finally:
                if not self.afs: # additional locking for NFS
                    fcntl.lockf(fd,fcntl.LOCK_UN)
                os.close(fd)
        except OSError, x:
            if x.errno != errno.ENOENT:
                raise RepositoryError(self.repo, "Error on session file access '%s': %s" % (fn,x))
        return Set()

    def session_write(self):
        """ Writes the locked set to the session file. 
            The global lock MUST be held for this function to work, although on NFS additional
            locking is done
            Raises RepositoryError if session file is inaccessible """
        try:
            # If this fails, we want to shutdown the repository (corruption possible)
            fd = os.open(self.fn,os.O_WRONLY)
            if not self.afs:
                fcntl.lockf(fd,fcntl.LOCK_EX)
            os.write(fd,pickle.dumps(self.locked))
            if not self.afs:
                fcntl.lockf(fd,fcntl.LOCK_UN)
            os.close(fd)
        except OSError, x:
            if x.errno != errno.ENOENT:
                raise RepositoryError(self.repo, "Error on session file access '%s': %s" % (self.fn,x))
            else:
                raise RepositoryError(self.repo, "Own session file not found! Possibly deleted by another ganga session.\n\
                                    Possible reasons could be that this computer has a very high load, or that the system clocks on computers running Ganga are not synchronized.\n\
                                    On computers with very high load and on network filesystems, try to avoid running concurrent ganga sessions for long.")
        except IOError, x:
            raise RepositoryError(self.repo, "Error on session file locking '%s': %s" % (self.fn,x))

    # counter read-write functions
    def cnt_read(self):
        """ Tries to read the counter file.
            Raises ValueError (invalid contents)
            Raises OSError (no access/does not exist)
            Raises RepositoryError (fatal)
            """
        try:
            fd = os.open(self.cntfn, os.O_RDONLY)
            try:
                if not self.afs: # additional locking for NFS
                    fcntl.lockf(fd,fcntl.LOCK_SH)
                return int(os.read(fd,100).split("\n")[0]) # 100 bytes should be enough for any ID. Can raise ValueErrorr
            finally:
                if not self.afs: # additional locking for NFS
                    fcntl.lockf(fd,fcntl.LOCK_UN)
                os.close(fd)
        except OSError, x:
            if x.errno != errno.ENOENT:
                raise RepositoryError(self.repo, "OSError on count file '%s' read: %s" % (self.cntfn, x))
            else:
                raise # This can be a recoverable error, depending on where it occurs
        except IOError, x:
            raise RepositoryError(self.repo, "Locking error on count file '%s' write: %s" % (self.cntfn, x))

    def cnt_write(self):
        """ Writes the counter to the counter file. 
            The global lock MUST be held for this function to work correctly
            Raises OSError if count file is inaccessible """
        try:
            # If this fails, we want to shutdown the repository (corruption possible)
            fd = os.open(self.cntfn,os.O_WRONLY)
            if not self.afs:
                fcntl.lockf(fd,fcntl.LOCK_EX)
            os.write(fd,str(self.count)+"\n")
            if not self.afs:
                fcntl.lockf(fd,fcntl.LOCK_UN)
            os.close(fd)
        except OSError, x:
            if x.errno != errno.ENOENT:
                raise RepositoryError(self.repo, "OSError on count file '%s' write: %s" % (self.cntfn, x))
            else:
                raise RepositoryError(self.repo, "Count file '%s' not found! Repository was modified externally!" % (self.cntfn))
        except IOError, x:
            raise RepositoryError(self.repo, "Locking error on count file '%s' write: %s" % (self.cntfn, x))

    # "User" functions
    def make_new_ids(self,n):
        """ Locks the next n available ids and returns them as a list 
            Raise RepositoryError on fatal error"""
        self.global_lock_acquire()
        try:
            # Actualize count
            try:
                newcount = self.cnt_read()
            except ValueError:
                logger.warning("Corrupt job counter (possibly due to crash of another session)! Trying to recover...")
                newcount = self.count
            except OSError:
                raise RepositoryError(self.repo, "Job counter deleted! External modification to repository!")
            if not newcount >= self.count:
                #raise RepositoryError(self.repo, "Counter value decreased - logic error!")
                logger.warning("Internal counter increased - probably the count file was deleted.")
                newcount = self.count
            if self.locked and max(self.locked) >= newcount: # someone used force_ids (for example old repository imports)
                newcount = max(self.locked) + 1
            ids = range(newcount,newcount+n)
            self.locked.update(ids)
            self.count = newcount+n
            self.cnt_write()
            self.session_write()
            return list(ids)
        finally:
            self.global_lock_release()

    def lock_ids(self,ids):
        ids = Set(ids)
        self.global_lock_acquire()
        try:
            try:
                sessions = [sn for sn in os.listdir(self.sdir) if sn.endswith(self.name+".locks")]
            except OSError, x:
                raise RepositoryError(self.repo, "Could not list session directory '%s'!" % (self.sdir))
                
            slocked = Set()
            for session in sessions:
                sf = os.path.join(self.sdir,session)
                if sf == self.fn:
                    continue
                slocked.update(self.session_read(sf))
            ids.difference_update(slocked)
            self.locked.update(ids)
            self.session_write()
            return list(ids)
        finally:
            self.global_lock_release()

    def release_ids(self,ids):
        self.global_lock_acquire()
        try:
            self.locked.difference_update(ids)
            self.session_write()
            return list(ids)
        finally:
            self.global_lock_release()



    def check(self):
        self.global_lock_acquire()
        try:
            f = file(self.cntfn)
            newcount = int(f.readline())
            f.close()
            assert newcount >= self.count
            sessions = os.listdir(self.sdir)
            prevnames = Set()
            for session in sessions:
                if not session.endswith(self.name+".locks"):
                    continue
                try:
                    sf = os.path.join(self.sdir,session)
                    fd = -1
                    if not self.afs:
                        fd = os.open(sf, os.O_RDONLY)
                        fcntl.lockf(fd,fcntl.LOCK_SH) # ONLY NFS
                    names = pickle.load(file(sf))
                    if not self.afs and fd > 0:
                        fcntl.lockf(fd,fcntl.LOCK_UN) # ONLY NFS
                        os.close(fd)
                except Exception, x:
                    logger.warning("CHECKER: session file %s corrupted: %s %s" % (session, x.__class__.__name__, x) )
                    continue
                if not len(names & prevnames) == 0:
                    print "Double-locked stuff:", names & prevnames
                    assert False
                prevnames.union_update(names)

        finally:
            self.global_lock_release()


    def get_lock_session(self,id): 
        """get_lock_session(id)
        Tries to determine the session that holds the lock on id for information purposes, and return an informative string.
        Returns None on failure
        """
        self.global_lock_acquire()
        try:
            sessions = [s for s in os.listdir(self.sdir) if s.endswith(self.name+".locks")]
            for session in sessions:
                try:
                    sf = os.path.join(self.sdir,session)
                    fd = -1
                    if not self.afs:
                        fd = os.open(sf, os.O_RDONLY)
                        fcntl.lockf(fd,fcntl.LOCK_SH) # ONLY NFS
                    names = pickle.load(file(sf))
                    if not self.afs and fd > 0:
                        fcntl.lockf(fd,fcntl.LOCK_UN) # ONLY NFS
                        os.close(fd)
                    if id in names:
                        return self.session_to_info(session)
                except Exception, x:
                    continue
        finally:
            self.global_lock_release()

    def get_other_sessions(self): 
        """get_session_list()
        Tries to determine the other sessions that are active and returns an informative string for each of them.
        """
        self.global_lock_acquire()
        try:
            sessions = [s for s in os.listdir(self.sdir) if s.endswith(".session") and not os.path.join(self.sdir,s) == self.gfn]
            return [self.session_to_info(session) for session in sessions]
        finally:
            self.global_lock_release()

    def reap_locks(self):
        """reap_locks() --> True/False
        Remotely clear all foreign locks from the session.
        WARNING: This is not nice.
        Returns True on success, False on error."""
        failed = False
        self.global_lock_acquire()
        try:
            sessions = [s for s in os.listdir(self.sdir) if s.endswith(".session") and not os.path.join(self.sdir,s) == self.gfn]
            for session in sessions:
                try:
                    sf = os.path.join(self.sdir,session)
                    os.unlink(sf)
                except OSError,x:
                    failed = True
            return not failed
        finally:
            self.global_lock_release()

    def session_to_info(self,session):
        si = session.split(".")
        try:
            return "%s (pid %s) since %s" % (".".join(si[:-3]),si[-2],time.ctime(int(si[-3])/1000))
        except Exception:
            return session

def test1():
    slm = SessionLockManager("locktest","tester")
    while True:
        print "lock  ---", slm.lock_ids(random.sample(xrange(100),3))
        print "unlock---", slm.release_ids(random.sample(xrange(100),3))
        slm.check()

def test2():
    slm = SessionLockManager("locktest","tester")
    while True:
        n = random.randint(1,9)
        print "get %i ids ---"%n, slm.make_new_ids(n)
        slm.check()

import random
if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        print "Usage: python SessionLock.py {1|2}"
        sys.exit(-1)
    if sys.argv[1] == "1":
        test1()
    elif sys.argv[1] == "2":
        test2()

