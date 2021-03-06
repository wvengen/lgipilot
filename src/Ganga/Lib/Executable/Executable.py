################################################################################
# Ganga Project. http://cern.ch/ganga
#
# $Id: Executable.py,v 1.1 2008-07-17 16:40:57 moscicki Exp $
################################################################################

from Ganga.GPIDev.Adapters.IApplication import IApplication
from Ganga.GPIDev.Adapters.IPrepareApp import IPrepareApp
from Ganga.GPIDev.Adapters.IRuntimeHandler import IRuntimeHandler
from Ganga.GPIDev.Schema import *

from Ganga.Utility.Config import getConfig

from Ganga.GPIDev.Lib.File import *
#from Ganga.GPIDev.Lib.File import File
#from Ganga.GPIDev.Lib.File import SharedDir
from Ganga.GPIDev.Lib.Registry.PrepRegistry import ShareRef
from Ganga.GPIDev.Base.Proxy import isType
from Ganga.Core import ApplicationConfigurationError

import os, shutil
from Ganga.Utility.files import expandfilename
shared_path = os.path.join(expandfilename(getConfig('Configuration')['gangadir']),'shared',getConfig('Configuration')['user'])

class Executable(IPrepareApp):
    """
    Executable application -- running arbitrary programs.
    
    When you want to run on a worker node an exact copy of your script you should specify it as a File object. Ganga will
    then ship it in a sandbox:
       app.exe = File('/path/to/my/script')

    When you want to execute a command on the worker node you should specify it as a string. Ganga will call the command
    with its full path on the worker node:
       app.exe = '/bin/date'

    A command string may be either an absolute path ('/bin/date') or a command name ('echo').
    Relative paths ('a/b') or directory paths ('/a/b/') are not allowed because they have no meaning
    on the worker node where the job executes.

    The arguments may be specified in the following way:
       app.args = ['-v',File('/some/input.dat')]

    This will yield the following shell command: executable -v input.dat
    The input.dat will be automatically added to the input sandbox.

    If only one argument is specified the the following abbreviation may be used:
       apps.args = '-v'
    
    """
    _schema = Schema(Version(2,0), {
        'exe' : SimpleItem(preparable=1,defvalue='echo',typelist=['str','Ganga.GPIDev.Lib.File.File.File'],comparable=1,doc='A path (string) or a File object specifying an executable.'), 
        'args' : SimpleItem(defvalue=["Hello World"],typelist=['str','Ganga.GPIDev.Lib.File.File.File','int'],sequence=1,strict_sequence=0,doc="List of arguments for the executable. Arguments may be strings, numerics or File objects."),
        'env' : SimpleItem(defvalue={},typelist=['str'],doc='Environment'),
        'is_prepared' : SimpleItem(defvalue=None, strict_sequence=0, visitable=1, copyable=1, typelist=['type(None)','bool'],protected=0,comparable=1,doc='Location of shared resources. Presence of this attribute implies the application has been prepared.'),
        'hash': SimpleItem(defvalue=None, typelist=['type(None)', 'str'], hidden=1, doc='MD5 hash of the string representation of applications preparable attributes')
        } )
    _category = 'applications'
    _name = 'Executable'
    _exportmethods = ['prepare', 'unprepare']
    _GUIPrefs = [ { 'attribute' : 'exe', 'widget' : 'File' },
                  { 'attribute' : 'args', 'widget' : 'String_List' },
                  { 'attribute' : 'env', 'widget' : 'DictOfString' } ]

    _GUIAdvancedPrefs = [ { 'attribute' : 'exe', 'widget' : 'File' },
                          { 'attribute' : 'args', 'widget' : 'String_List' },
                          { 'attribute' : 'env', 'widget' : 'DictOfString' } ]

    def __init__(self):
        super(Executable,self).__init__()

    def unprepare(self, force=False):
        """
        Revert an Executable() application back to it's unprepared state.
        """
        logger.debug('Running unprepare in Executable app')
        if self.is_prepared is not None:
            self.decrementShareCounter(self.is_prepared.name)
            self.is_prepared = None
        self.hash = None

    def prepare(self,force=False):
        """
        A method to place the Executable application into a prepared state.

        The application wil have a Shared Directory object created for it. 
        If the application's 'exe' attribute references a File() object or
        is a string equivalent to the absolute path of a file, the file 
        will be copied into the Shared Directory.

        Otherwise, it is assumed that the 'exe' attribute is referencing a 
        file available in the user's path (as per the default "echo Hello World"
        example). In this case, a wrapper script which calls this same command 
        is created and placed into the Shared Directory.

        When the application is submitted for execution, it is the contents of the
        Shared Directory that are shipped to the execution backend. 

        The Shared Directory contents can be queried with 
        shareref.ls('directory_name')
        
        See help(shareref) for further information.
        """

        if (self.is_prepared is not None) and (force is not True):
            raise Exception('%s application has already been prepared. Use prepare(force=True) to prepare again.'%(self._name))


        #lets use the same criteria as the configure() method for checking file existence & sanity
        #this will bail us out of prepare if there's somthing odd with the job config - like the executable
        #file is unspecified, has a space or is a relative path
        self.configure(self)
        logger.info('Preparing %s application.'%(self._name))
        self.is_prepared = ShareDir()
        logger.info('Created shared directory: %s'%(self.is_prepared.name))

        #copy any 'preparable' objects into the shared directory
        send_to_sharedir = self.copyPreparables()
        #add the newly created shared directory into the metadata system if the app is associated with a persisted object
        self.checkPreparedHasParent(self)
        #return [os.path.join(self.is_prepared.name,os.path.basename(send_to_sharedir))]
        self.post_prepare()
        return 1


    def configure(self,masterappconfig):
        from Ganga.Core import ApplicationConfigurationError
        import os.path
        
        # do the validation of input attributes, with additional checks for exe property

        def validate_argument(x,exe=None):
            if type(x) is type(''):
                if exe:
                    if not x:
                        raise ApplicationConfigurationError(None,'exe not specified')
                        
                    if len(x.split())>1:
                        raise ApplicationConfigurationError(None,'exe "%s" contains white spaces'%x)

                    dirn,filen = os.path.split(x)
                    if not filen:
                        raise ApplicationConfigurationError(None,'exe "%s" is a directory'%x)
                    if dirn and not os.path.isabs(dirn) and self.is_prepared is None:
                        raise ApplicationConfigurationError(None,'exe "%s" is a relative path'%x)
                    if not os.path.basename(x) == x:
                        if not os.path.isfile(x):
                            raise ApplicationConfigurationError(None,'%s: file not found'%x)

            else:
              try:
                  #int arguments are allowed -> later converted to strings      
                  if isinstance(x,int):
                      return
                  if not x.exists():
                      raise ApplicationConfigurationError(None,'%s: file not found'%x.name)
              except AttributeError:
                  raise ApplicationConfigurationError(None,'%s (%s): unsupported type, must be a string or File'%(str(x),str(type(x))))
                
        validate_argument(self.exe,exe=1)

        for a in self.args:
            validate_argument(a)
        
        return (None,None)

# disable type checking for 'exe' property (a workaround to assign File() objects)
# FIXME: a cleaner solution, which is integrated with type information in schemas should be used automatically
config = getConfig('defaults_Executable') #_Properties
#config.setDefaultOption('exe',Executable._schema.getItem('exe')['defvalue'], type(None),override=True)
config.options['exe'].type = type(None)

# not needed anymore: 
#   the backend is also required in the option name
#   so we need a kind of dynamic options (5.0)
#mc = getConfig('MonitoringServices')
#mc['Executable'] = None

def convertIntToStringArgs(args):

    result = []
    
    for arg in args:
        if isinstance(arg,int):
            result.append(str(arg))
        else:
            result.append(arg)

    return result

class RTHandler(IRuntimeHandler):
    def prepare(self,app,appconfig,appmasterconfig,jobmasterconfig):
        from Ganga.GPIDev.Adapters.StandardJobConfig import StandardJobConfig

        prepared_exe = app.exe
        if app.is_prepared is not None:
            if type(app.exe) is str:
                #we have a file. is it an absolute path?
                if os.path.abspath(app.exe) == app.exe:
                    logger.info("Submitting a prepared application; taking any input files from %s" %(app.is_prepared.name))
                    prepared_exe = File(os.path.join(os.path.join(shared_path,app.is_prepared.name),os.path.basename(File(app.exe).name)))
                #else assume it's a system binary, so we don't need to transport anything to the sharedir
                else:
                    prepared_exe = app.exe
            elif type(app.exe) is File:
                logger.info("Submitting a prepared application; taking any input files from %s" %(app.is_prepared.name))
                prepared_exe = File(os.path.join(os.path.join(shared_path,app.is_prepared.name),os.path.basename(app.exe.name)))

        c = StandardJobConfig(prepared_exe,app._getParent().inputsandbox,convertIntToStringArgs(app.args),app._getParent().outputsandbox,app.env)
        return c
        

class DiracRTHandler(IRuntimeHandler):
    def prepare(self,app,appconfig,appmasterconfig,jobmasterconfig):
        from Ganga.GPIDev.Lib.File import File
        rth=RTHandler()
        prep=rth.prepare(app,appconfig)
        ## Modify result in order to run on Dirac

        result={}
        result['vers']=''
        result['opts']=''
        result['app']=prep['jobscript']
        result['inputbox']=prep['inputbox']
        result['dlls']=''
        return result

class LCGRTHandler(IRuntimeHandler):
    def prepare(self,app,appconfig,appmasterconfig,jobmasterconfig):
        from Ganga.Lib.LCG import LCGJobConfig

        prepared_exe = app.exe
        if app.is_prepared is not None:
            if type(app.exe) is str:
                #we have a file. is it an absolute path?
                if os.path.abspath(app.exe) == app.exe:
                    logger.info("Submitting a prepared application; taking any input files from %s" %(app.is_prepared.name))
                    prepared_exe = File(os.path.join(os.path.join(shared_path,app.is_prepared.name),os.path.basename(File(app.exe).name)))
                #else assume it's a system binary, so we don't need to transport anything to the sharedir
                else:
                    prepared_exe = app.exe
            elif type(app.exe) is File:
                logger.info("Submitting a prepared application; taking any input files from %s" %(app.is_prepared.name))
                prepared_exe = File(os.path.join(os.path.join(shared_path,app.is_prepared.name),os.path.basename(app.exe.name)))

        return LCGJobConfig(prepared_exe,app._getParent().inputsandbox,convertIntToStringArgs(app.args),app._getParent().outputsandbox,app.env)

class gLiteRTHandler(IRuntimeHandler):
    def prepare(self,app,appconfig,appmasterconfig,jobmasterconfig):
        from Ganga.Lib.gLite import gLiteJobConfig

        prepared_exe = app.exe
        if app.is_prepared is not None:
            if type(app.exe) is str:
                #we have a file. is it an absolute path?
                if os.path.abspath(app.exe) == app.exe:
                    logger.info("Submitting a prepared application; taking any input files from %s" %(app.is_prepared.name))
                    prepared_exe = File(os.path.join(os.path.join(shared_path,app.is_prepared.name),os.path.basename(File(app.exe).name)))
                #else assume it's a system binary, so we don't need to transport anything to the sharedir
                else:
                    prepared_exe = app.exe
            elif type(app.exe) is File:
                logger.info("Submitting a prepared application; taking any input files from %s" %(app.is_prepared.name))
                prepared_exe = File(os.path.join(os.path.join(shared_path,app.is_prepared.name),os.path.basename(File(app.exe).name)))

        return gLiteJobConfig(prepared_exe,app._getParent().inputsandbox,convertIntToStringArgs(app.args),app._getParent().outputsandbox,app.env)
from Ganga.GPIDev.Adapters.ApplicationRuntimeHandlers import allHandlers

allHandlers.add('Executable','LSF', RTHandler)
allHandlers.add('Executable','Local', RTHandler)
allHandlers.add('Executable','PBS', RTHandler)
allHandlers.add('Executable','SGE', RTHandler)
allHandlers.add('Executable','Condor', RTHandler)
allHandlers.add('Executable','LCG', LCGRTHandler)
allHandlers.add('Executable','gLite', gLiteRTHandler)
allHandlers.add('Executable','TestSubmitter', RTHandler)
allHandlers.add('Executable','Interactive', RTHandler)
allHandlers.add('Executable','Batch', RTHandler)
allHandlers.add('Executable','Cronus', RTHandler)
allHandlers.add('Executable','Remote', LCGRTHandler)
allHandlers.add('Executable','CREAM', LCGRTHandler)

