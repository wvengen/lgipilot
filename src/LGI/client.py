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

from connection import Connection, LGIException


class LGIClientException(LGIException):
    pass

class Client(Connection):

    def __init__(self, url=None, project=None, user=None, groups=None, certificate=None, privateKey=None, caChain=None):
        '''initialize LGI client connection with parameters or defaults read from ~/.LGI'''
        Connection.__init__(self, url, project, certificate, privateKey, caChain)
        self._user = user
        self._groups = groups
        if not self._user:
            self._user = self.__readConfig("user")
        if not self._groups:
            self._groups = self.__readConfig("groups")
        if not self._url:
            self._url = self.__readConfig("defaultserver")
        if not self._project:
            self._project = self.__readConfig("defaultproject")
        if not self._certificate:
            self._certificate = os.path.join(os.getenv("HOME"), '.LGI', 'certificate')
        if not self._privateKey:
            self._privateKey= os.path.join(os.getenv("HOME"), '.LGI', 'privatekey')
        if not self._caChain:
            self._caChain= os.path.join(os.getenv("HOME"), '.LGI', 'ca_chain')

    def jobState(self, jobId):
        '''request state of job'''
        args =  {'project': self._project,
                 'user': self._user,
                 'groups': self._groups}
        if jobId: args['job_id'] = jobId
        ret = self._postToServer("/interfaces/interface_job_state.php", args)
        return ret['LGI']['response']

    def jobList(self, application=None, state=None, start=None, limit=None):
        '''retrieve list of jobs'''
        args = {'project': self._project,
                'user': self._user,
                'groups': self._groups}
        if application: args['application'] = application
        if state: args['state'] = state
        if start: args['start'] = start
        if limit: args['limit'] = limit
        ret = self._postToServer("/interfaces/interface_job_state.php", args)
        ret = ret['LGI']['response']
        if type(ret['job']) != list: ret['job'] = [ ret['job']]
        return ret

    def jobDelete(self, jobId):
        '''delete a job'''
        args =  {'project': self._project,
                 'user': self._user,
                 'groups': self._groups}
        if jobId: args['job_id'] = jobId
        ret = self._postToServer("/interfaces/interface_delete_job.php", args)
        return ret['LGI']['response']

    def jobSubmit(self, application, targetResources="any", input_=None, jobSpecifics=None, writeAccess=None, readAccess=None, files=[]):
        '''submit a job for given application and options'''
        args = {'project': self._project,
                'user': self._user,
                'groups': self._groups,
                'number_of_uploaded_files': 0}
        if application: args['application'] = application
        if targetResources: args['target_resources'] = targetResources
        if writeAccess: args['write_access'] = writeAccess
        if readAccess: args['read_access'] = readAccess
        if input_: args['input'] = binascii.b2a_hex(input_)
        fileargs = {}
        for filename in files:
            args['number_of_uploaded_files'] += 1
            f = open(filename, "r")
            fileargs['uploaded_file_%d'%args['number_of_uploaded_files']] = (filename, f.read())
            f.close()
        ret = self._postToServer("/interfaces/interface_submit_job.php", args, fileargs)
        return ret['LGI']['response']

    def resourceList(self):
        '''retrieve resource list'''
        ret = self._postToServer("/interfaces/interface_project_resource_list.php", {
                'project': self._project,
                'user': self._user,
                'groups': self._groups})
        return ret['LGI']['response']

    def serverList(self):
        '''retrieve project server list'''
        ret = self._postToServer("/interfaces/interface_project_server_list.php", {
                'project': self._project,
                'user': self._user,
                'groups': self._groups})
        return ret['LGI']['response']

    def __readConfig(self, filename):
        '''return contents of configuration file relative to directory ~/.LGI'''
        f = open(os.path.join(os.getenv('HOME'), '.LGI', filename), "r");
        data = f.read()
        f.close()
        return data.rstrip( "\n\r\t ")

# vim:ts=4:sw=4:expandtab:
