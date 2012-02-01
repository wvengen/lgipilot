#
# Copyright (C) 2011 W. van Engen, Stichting FOM, The Netherlands
# Copyright (C) 2010 M.F. Somers, Theoretical Chemistry Group, Leiden University
#
# This is free software; you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation.
#
# http://www.gnu.org/licenses/gpl.txt

import os
import binascii
import xml.dom.minidom
import xml2dict
from connection import Connection, LGIException


class LGIClientException(LGIException):
    '''LGI client exception'''
    pass


class Client(Connection):
    '''Client for the interface interface of the LGI project server.'''

    def __init__(self, url=None, project=None, user=None, groups=None, certificate=None, privateKey=None, caChain=None):
        '''Initialize LGI client connection.

        Configuration can be supplied as parameters, or else defaults will
        be read from the first existing file/directory out of this list:

        @type url str
        @param url LGI project server url to work with
        @type project str
        @param project LGI project to work with
        @type user str
        @param user LGI username
        @type groups str
        @param groups LGI groups
        @type certificate str
        @param certificate location of user certificate file
        @type privateKey str
        @param privateKey location of user private key file
        @type caChain str
        @param caChain location of CA chain to validate LGI project server with
        '''
        Connection.__init__(self, url, project, certificate, privateKey, caChain)
        self.readConfig()
        if url is not None: self._url = url
        if project is not None: self._project = project
        if certificate is not None: self._certificate = certificate
        if privateKey is not None: self._privateKey = privateKey
        if caChain is not None: self._chChain = caChain
        if user is not None: self._user = user
        if groups is not None: self._groups = groups

    def readConfig(self, cfg=None):
        '''Read configuration from file or directory.

        When the parameter is not specified, the default configuration will
        be read, from
        * where the LGI_CONFIG environment variable points to, or else
        * the file ~/.LGI/LGI.cfg, or else
        * the directory ~/.LGI, or else
        * the file ~/LGI.cfg
        A configuration file has an xml-like format, while a configuration
        directory consists of separate files for each configuration item.
        @see https://github.com/wvengen/LGI/wiki/User-configuration

        @type frm str
        @param frm Path to configuration file or configuration directory'''
        if not cfg:
            cfg = os.getenv('LGI_CONFIG')
            if not cfg or not os.path.exists(cfg):
                cfg = os.path.join(os.path.expanduser('~'), '.LGI', 'LGI.cfg')
                if not os.path.exists(cfg):
                    cfg = os.path.join(os.path.expanduser('~'), '.LGI')
                    if not os.path.exists(cfg):
                        cfg = os.path.join(os.path.expanduser('~'), 'LGI.cfg')
        if os.path.isdir(cfg):
            self.__readConfig_dir(cfg)
        else:
            self.__readConfig_file(cfg)

    def jobState(self, jobId):
        '''Request state of job.

        @type jobId int
        @param jobId job id to query
        @rtype dict
        @return parsed project server response
        '''
        args =  {'project': self._project,
                 'user': self._user,
                 'groups': self._groups}
        if jobId is not None: args['job_id'] = jobId
        ret = self._postToServer("/interfaces/interface_job_state.php", args)
        return ret['LGI']['response']

    def jobList(self, application=None, state=None, start=None, limit=None):
        '''Retrieve list of jobs.

        @type application str
        @param application application to restrict to, or None for all applications
        @type state str
        @param state state to restrict to, or None for all states
        @type start int
        @param start start listing at this index
        @type limit int
        @param limit maximum number of jobs to return
        @rtype dict
        @return parsed project server response
        '''
        args = {'project': self._project,
                'user': self._user,
                'groups': self._groups}
        if application is not None: args['application'] = application
        if state is not None: args['state'] = state
        if start is not None: args['start'] = start
        if limit is not None: args['limit'] = limit
        ret = self._postToServer("/interfaces/interface_job_state.php", args)
        ret = ret['LGI']['response']
        if type(ret['job']) != list: ret['job'] = [ ret['job']]
        return ret

    def jobDelete(self, jobId):
        '''Delete a job.

        @type jobId int
        @param jobId job id to delete
        @rtype dict
        @return parsed project server response
        '''
        args =  {'project': self._project,
                 'user': self._user,
                 'groups': self._groups}
        if jobId is not None: args['job_id'] = jobId
        ret = self._postToServer("/interfaces/interface_delete_job.php", args)
        return ret['LGI']['response']

    def jobSubmit(self, application, input_=None, targetResources="any", jobSpecifics=None, writeAccess=None, readAccess=None, files=[]):
        '''Submit a job.

        @type application str
        @param application application to submit to
        @type input_ str
        @param input_ input for job
        @type targetResources str
        @param targetResources comma-separated list of target_resources to submit to, or 'any'
        @type jobSpecifics str
        @param jobSpecifics job_specifics
        @type writeAccess str
        @param writeAccess comma-separated list of people to give write access
        @type readAccess str
        @param readAccess comma-separated list of people to give read access
        @type files list(str)
        @param files paths of files to upload 
        @rtype dict
        @return parsed project server response
        '''
        args = {'project': self._project,
                'user': self._user,
                'groups': self._groups,
                'number_of_uploaded_files': 0}
        if application is not None: args['application'] = application
        if targetResources is not None: args['target_resources'] = targetResources
        if writeAccess is not None: args['write_access'] = writeAccess
        if readAccess is not None: args['read_access'] = readAccess
        if input_ is not None: args['input'] = binascii.b2a_hex(input_)
        fileargs = {}
        for filename in files:
            args['number_of_uploaded_files'] += 1
            f = open(filename, "r")
            fileargs['uploaded_file_%d'%args['number_of_uploaded_files']] = (filename, f.read())
            f.close()
        ret = self._postToServer("/interfaces/interface_submit_job.php", args, fileargs)
        return ret['LGI']['response']

    def resourceList(self):
        '''Retrieve resource list.
        @rtype dict
        @return parsed project server response
        '''
        ret = self._postToServer("/interfaces/interface_project_resource_list.php", {
                'project': self._project,
                'user': self._user,
                'groups': self._groups})
        return ret['LGI']['response']

    def serverList(self):
        '''Retrieve project server list.
        @type dict
        @return parsed project server response
        '''
        ret = self._postToServer("/interfaces/interface_project_server_list.php", {
                'project': self._project,
                'user': self._user,
                'groups': self._groups})
        return ret['LGI']['response']

    def __readConfig_dir(self, directory):
        '''Parse a configuration directory'''
        self._user = self.__readConfig_readfile(directory, 'user')
        self._groups = self.__readConfig_readfile(directory, 'groups')
        self._url = self.__readConfig_readfile(directory, 'defaultserver')
        self._project = self.__readConfig_readfile(directory, 'defaultproject')
        self._certificate = os.path.abspath(os.path.join(directory, 'certificate'))
        self._privateKey = os.path.abspath(os.path.join(directory, 'privatekey'))
        self._caChain = os.path.abspath(os.path.join(directory, 'ca_chain'))

    def __readConfig_file(self, filename):
        '''Parse a configuration file'''
        cfg = xml2dict.xml2dict(xml.dom.minidom.parse(filename))
        if not 'LGI_user_config' in cfg:
            raise LGIClientException('Invalid LGI user configuration: %s'%filename)
        cfg = cfg['LGI_user_config']
        self._user = cfg['user']
        self._groups = cfg['groups']
        self._url = cfg['defaultserver']
        self._project = cfg['defaultproject']
        self._certificate = os.path.abspath(filename)
        self._privateKey = os.path.abspath(filename)
        self._caChain = os.path.abspath(filename)

    def __readConfig_readfile(self, directory, filename):
        '''Return the contents of a text file'''
        f = open(os.path.join(directory, filename), "r");
        data = f.read()
        f.close()
        result = data.rstrip( "\n\r\t ")
        return result


# vim:ts=4:sw=4:expandtab:
