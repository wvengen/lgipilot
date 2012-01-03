################################################################################
# Ganga Project. http://cern.ch/ganga
#
# $Id: MassStorageFile.py,v 0.1 2011-11-09 15:40:00 idzhunov Exp $
################################################################################

from Ganga.GPIDev.Schema import *

from OutputFile import OutputFile

class MassStorageFile(OutputFile):
    """MassStorageFile represents a class marking a file to be written into mass storage (like Castor at CERN)
    """
    _schema = Schema(Version(1,1), {'name': SimpleItem(defvalue="",doc='name of the file')})
    _category = 'outputfiles'
    _name = "MassStorageFile"
    _location = []
    _exportmethods = [ "location" , "get", "setLocation" ]
        
    def __init__(self,name='', **kwds):
        """ name is the name of the output file that has to be written into mass storage
        """
        super(MassStorageFile, self).__init__(name, **kwds)
        self._location = []

    def __construct__(self,args):
        super(MassStorageFile,self).__construct__(args)

            
    def __repr__(self):
        """Get the representation of the file."""

        return "MassStorageFile(name='%s')"% self.name
    

    def setLocation(self, location):
        """
        Return list with the locations of the post processed files (if they were configured to upload the output somewhere)
        """
        if location not in self._location:
            self._location.append(location)
        
    def location(self):
        """
        Return list with the locations of the post processed files (if they were configured to upload the output somewhere)
        """
        return self._location

    def get(self, dir):
        """
        Retrieves locally all files matching this OutputFile object pattern
        """
        import os

        if not os.path.isdir(dir):
            print "%s is not a valid directory.... " % dir
            return

        from Ganga.Utility.Config import getConfig 
        cp_cmd = getConfig('MassStorageOutput')['cp_cmd']  
        

        for location in self._location:
            targetLocation = os.path.join(dir, os.path.basename(location))      
            os.system('%s %s %s' % (cp_cmd, location, targetLocation))


# add MassStorageFile objects to the configuration scope (i.e. it will be possible to write instatiate MassStorageFile() objects via config file)
import Ganga.Utility.Config
Ganga.Utility.Config.config_scope['MassStorageFile'] = MassStorageFile
