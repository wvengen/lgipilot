################################################################################
# Ganga Project. http://cern.ch/ganga
#
# $Id: MassStorageFile.py,v 0.1 2011-11-09 15:40:00 idzhunov Exp $
################################################################################

import os
from Ganga.GPIDev.Schema import *

from Ganga.Utility.Config import getConfig

from OutputSandboxFile import OutputSandboxFile

class MassStorageFile(OutputSandboxFile):
    """MassStorageFile represents a class marking a file to be written into mass storage (like Castor at CERN)
    """
    _schema = Schema(Version(1,1), {'name': SimpleItem(defvalue="",doc='name of the file'),
                                    'joboutputdir': SimpleItem(defvalue="",doc='outputdir of the job with which the outputsandbox file object is associated'),
                                    'locations' : SimpleItem(defvalue=[],typelist=['str'],sequence=1,doc="list of locations where the outputfiles are uploaded"),
                                    'compressed' : SimpleItem(defvalue=False, typelist=['bool'],protected=0,doc='wheather the output file should be compressed before sending somewhere')
                                        })

    _category = 'outputfiles'
    _name = "MassStorageFile"
    _exportmethods = [ "location" , "get", "setLocation" ]
        
    def __init__(self,name='', **kwds):
        """ name is the name of the output file that has to be written into mass storage
        """
        super(MassStorageFile, self).__init__(name, **kwds)
        self.locations = []

    def __construct__(self,args):
        super(MassStorageFile,self).__construct__(args)

            
    def __repr__(self):
        """Get the representation of the file."""

        return "MassStorageFile(name='%s')"% self.name
    

    def setLocation(self):
        """
        Sets the location of output files that were uploaded to mass storage from the WN
        """
        
        postprocessLocationsPath = os.path.join(self.joboutputdir, getConfig('Output')['PostProcessLocationsFileName'])
        if not os.path.exists(postprocessLocationsPath):
            return

        postprocesslocations = open(postprocessLocationsPath, 'r')
        
        for line in postprocesslocations.readlines():
                
            if line.strip() == '':      
                continue

            lineParts = line.split(' ') 
            outputPattern = lineParts[1]
            outputPath = lineParts[2]           

            if line.startswith('massstorage'):

                if outputPattern == self.name:
                    massStorageLocation = outputPath.strip('\n')        
                    if massStorageLocation not in self.locations:
                        self.locations.append(massStorageLocation)
     
        postprocesslocations.close()
            
        
    def location(self):
        """
        Return list with the locations of the post processed files (if they were configured to upload the output somewhere)
        """
        return self.locations

    def get(self, dir):
        """
        Retrieves locally all files matching this MassStorageFile object pattern
        """

        if not os.path.isdir(dir):
            print "%s is not a valid directory.... " % dir
            return

         
        cp_cmd = getConfig('Output')['MassStorageFile']['uploadOptions']['cp_cmd']  

        for location in self.locations:
            targetLocation = os.path.join(dir, os.path.basename(location))      
            os.system('%s %s %s' % (cp_cmd, location, targetLocation))

    def put(self):
        """
        Creates and executes commands for file upload to mass storage (Castor), this method will
        be called on the client
        """     
        import glob
        import re

        massStorageConfig = getConfig('Output')['MassStorageFile']['uploadOptions']

        #if Castor mass storage (we understand from the nsls command)
        if massStorageConfig['ls_cmd'] == 'nsls':
            host = getConfig('System')['GANGA_HOSTNAME']
            lxplusHost = re.match('lxplus.*cern\.ch', host)
            if lxplusHost is None:
                logger.warning('Output files can be uploaded to Castor only from lxplus')
                logger.warning('skipping %s for uploading to Castor' % outputFile.name)
                return 

            mkdir_cmd = massStorageConfig['mkdir_cmd']
            cp_cmd = massStorageConfig['cp_cmd']
            ls_cmd = massStorageConfig['ls_cmd']
            massStoragePath = massStorageConfig['path']

            pathToDirName = os.path.dirname(massStoragePath)
            dirName = os.path.basename(massStoragePath)

            (exitcode, mystdout, mystderr) = self.execSyscmdSubprocess('nsls %s' % pathToDirName)
            if exitcode != 0:
                logger.warning('Error while executing nsls %s command, be aware that Castor commands can be executed only from lxplus, also check if the folder name is correct and existing' % pathToDirName, mystderr)
                logger.warning('skipping %s for uploading to Castor' % outputFile.name)
                return

            directoryExists = False 
            for directory in mystdout.split('\n'):
                if directory.strip() == dirName:
                    directoryExists = True
                    break

            if not directoryExists:
                (exitcode, mystdout, mystderr) = self.execSyscmdSubprocess('%s %s' % (mkdir_cmd, massStoragePath))
                if exitcode != 0:
                    logger.warning('Error while executing %s %s command, check if the ganga user has rights for creating directories in this folder' % (mkdir_cmd, massStoragePath))
                    logger.warning('skipping %s for uploading to Castor' % outputFile.name)
                    return
            
            fileName = self.name
            if self.compressed:
                fileName = '%s.gz' % self.name 

            for currentFile in glob.glob(os.path.join(self.joboutputdir, fileName)):
                (exitcode, mystdout, mystderr) = self.execSyscmdSubprocess('%s %s %s' % (cp_cmd, currentFile, massStoragePath))
                if exitcode != 0:
                    logger.warning('Error while executing %s %s %s command, check if the ganga user has rights for uploading files to this mass storage folder' % (cp_cmd, currentFile, massStoragePath))
                else:
                    logger.info('%s successfully uploaded to mass storage' % currentFile)              
                    location = os.path.join(massStoragePath, os.path.basename(currentFile))
                    if location not in self.locations:
                        self.locations.append(location)         
                    #remove file from output
                    os.system('rm %s' % os.path.join(self.joboutputdir, currentFile))



    def getWNInjectedScript(self, outputFiles, indent, patternsToZip, postProcessLocationsFP):
        """
        Returns script that have to be injected in the jobscript for postprocessing on the WN
        """        
        massStorageCommands = []
      
        massStorageConfig = getConfig('Output')['MassStorageFile']['uploadOptions']  

        for outputFile in outputFiles:
            massStorageCommands.append('massstorage %s %s %s %s %s' % (outputFile.name , massStorageConfig['mkdir_cmd'],  massStorageConfig['cp_cmd'], massStorageConfig['ls_cmd'], massStorageConfig['path'])) 

                
        script = """\n

###INDENT####system command executor with subprocess
###INDENT###def execSyscmdSubprocessAndReturnOutputMAS(cmd):

###INDENT###    exitcode = -999
###INDENT###    mystdout = ''
###INDENT###    mystderr = ''

###INDENT###    try:
###INDENT###        child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
###INDENT###        (mystdout, mystderr) = child.communicate()
###INDENT###        exitcode = child.returncode
###INDENT###    finally:
###INDENT###        pass

###INDENT###    return (exitcode, mystdout, mystderr)
        
###INDENT###for massStorageLine in ###MASSSTORAGECOMMANDS###:
###INDENT###    massStorageList = massStorageLine.split(' ')

###INDENT###    filenameWildChar = massStorageList[1]
###INDENT###    cm_mkdir = massStorageList[2]
###INDENT###    cm_cp = massStorageList[3]
###INDENT###    cm_ls = massStorageList[4]
###INDENT###    path = massStorageList[5]

###INDENT###    pathToDirName = os.path.dirname(path)
###INDENT###    dirName = os.path.basename(path)

###INDENT###    (exitcode, mystdout, mystderr) = execSyscmdSubprocessAndReturnOutputMAS('nsls %s' % pathToDirName)
###INDENT###    if exitcode != 0:
###INDENT###        printError('Error while executing nsls %s command, be aware that Castor commands can be executed only ###INDENT###from lxplus, also check if the folder name is correct and existing' % pathToDirName + os.linesep + mystderr)
###INDENT###        continue

###INDENT###    directoryExists = False 
###INDENT###    for directory in mystdout.split('\\n'):
###INDENT###        if directory.strip() == dirName:
###INDENT###            directoryExists = True
###INDENT###            break

###INDENT###    if not directoryExists:
###INDENT###        (exitcode, mystdout, mystderr) = execSyscmdSubprocessAndReturnOutputMAS('%s %s' % (cm_mkdir, path))
###INDENT###        if exitcode != 0:
###INDENT###            printError('Error while executing %s %s command, check if the ganga user has rights for creating ###INDENT###directories in this folder' % (cm_mkdir, path) + os.linesep + mystderr)
###INDENT###            continue
   
###INDENT###    filenameWildCharZipped = filenameWildChar
###INDENT###    if filenameWildChar in ###PATTERNSTOZIP###:
###INDENT###        filenameWildCharZipped = '%s.gz' % filenameWildChar

###INDENT###    for currentFile in glob.glob(os.path.join(os.getcwd(),filenameWildCharZipped)):
###INDENT###        currentFileBaseName = os.path.basename(currentFile)
###INDENT###        (exitcode, mystdout, mystderr) = execSyscmdSubprocessAndReturnOutputMAS('%s %s %s' % (cm_cp, currentFile, os.path.join(path, currentFileBaseName)))
###INDENT###        if exitcode != 0:
###INDENT###            printError('Error while executing %s %s %s command, check if the ganga user has rights for uploading ###INDENT###files to this mass storage folder' % (cm_cp, currentFile, os.path.join(path, currentFileBaseName)) + os.linesep ###INDENT### + mystderr)
###INDENT###        else:
###INDENT###            ###POSTPROCESSLOCATIONSFP###.write('massstorage %s %s\\n' % (filenameWildChar, os.path.join(path, currentFileBaseName)))
###INDENT###            #remove file from output dir
###INDENT###            os.system('rm %s' % currentFile)
"""

        script = script.replace('###MASSSTORAGECOMMANDS###', str(massStorageCommands))
        script = script.replace('###PATTERNSTOZIP###', str(patternsToZip))
        script = script.replace('###INDENT###', indent)
        script = script.replace('###POSTPROCESSLOCATIONSFP###', postProcessLocationsFP)

        return script   

# add MassStorageFile objects to the configuration scope (i.e. it will be possible to write instatiate MassStorageFile() objects via config file)
import Ganga.Utility.Config
Ganga.Utility.Config.config_scope['MassStorageFile'] = MassStorageFile
