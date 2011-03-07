#
# Copyright (C) 2011 W. van Engen, Stichting FOM, The Netherlands
# Copyright (C) 2010 M.F. Somers, Theoretical Chemistry Group, Leiden University
#
# This is free software; you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation.
#
# http://www.gnu.org/licenses/gpl.txt

import os
import sys
import xml.dom.minidom
import tempfile
import tarfile

import xml2dict
from connection import Connection, LGIException


class LGIResourceException(LGIException):
    pass

class Resource(Connection):
    '''LGI connection for resources. This is a thin layer: each command just
    returns the server's /LGI/response/* parsed into a dict, unless otherwise
    mentioned.'''

    def __init__(self, urlOrCfg, project=None, certificate=None, privateKey=None, caChain=None):
        '''Initialize resource, either by specifying all components or by only giving
        the first parameter pointing to a resource daemon configuration file. Instead of
        a resource daemon configuration file, it can also point to a tarball containing
        LGI.cfg as resource daemon configuration file and certificates.'''
        self._apps = None
        self._sessionId = None
        self._tmpdir = None
        if project:
            Connection.__init__(self, urlOrCfg, project, certificate, privateKey, caChain)
        else:
            Connection.__init__(self, None, None, None, None, None)
            if tarfile.is_tarfile(urlOrCfg):
                self.parseTarball(urlOrCfg)
            else:
                self.parseConfig(urlOrCfg)

    def parseConfig(self, LGIconf, reldir=None):
        '''Load info from resource daemon configuration file. If reldir is
        given, relative file paths for certificates are resolved to this
        directory. If reldir is None and LGIconf is a filename, reldir is
        assumed to be the dirname of LGIconf. If reldir is None and LGIconf 
        is a file object, relative paths are retained.'''

        if not LGIconf: return

        conf = xml2dict.xml2dict(xml.dom.minidom.parse(LGIconf))

        if not reldir and isinstance(LGIconf, str):
            reldir = os.path.dirname(LGIconf)
        cert = conf['LGI']['resource']['resource_certificate_file']
        if reldir and not os.path.isabs(cert):
            cert = os.path.join(reldir, cert)
        self._certificate = cert

        key = conf['LGI']['resource']['resource_key_file']
        if reldir and not os.path.isabs(key):
            key = os.path.join(reldir, key)
        self._privateKey = key

        ca = conf['LGI']['ca_certificate_file']
        if reldir and not os.path.isabs(ca):
            ca = os.path.join(reldir, ca)
        self._caChain = ca

        project = conf['LGI']['resource']['project']
        if isinstance(project, list):
            raise LGIResourceException("Only one project allowed in LGI configuration right now")
        self._url = project['project_master_server']
        self._project = project['project_name']
        if not isinstance(project['application'], list):
            project['application'] = [ project['application'] ]

        apps = map(lambda x: x['application_name'], project['application'])
        self.setApplications(apps)

    def parseTarball(self, tarball, cfg='LGI.cfg'):
        '''Parse configuration from a tarball containing a resource daemon
        configuration file and certificates. This extracts the certificates as
        temporary files to be used for authentication, which are removed upon
        deletion of this object.'''
        dist = tarfile.open(tarball, 'r')
        # get info from config
        fileprefix = ''
        try:
            conf = dist.extractfile(cfg)
        except KeyError:
            fileprefix = './'
            conf = dist.extractfile(fileprefix+cfg)

        self._tmpdir = tempfile.mkdtemp('.tmp','lgipilot.')
        self.parseConfig(conf)

        # figure out which certificate files need to be extracted
        xfiles = []
        if not os.path.isabs(self._certificate):
            xfiles.append((self._certificate, 'certificate'))
            self._certificate = os.path.join(self._tmpdir, 'certificate')
        if not os.path.isabs(self._privateKey):
            xfiles.append((self._privateKey, 'privatekey'))
            self._privateKey = os.path.join(self._tmpdir, 'privatekey')
        if not os.path.isabs(self._caChain):
            xfiles.append((self._caChain, 'ca_chain'))
            self._caChain = os.path.join(self._tmpdir, 'ca_chain')
        # extract each to designated file
        for xfile,newname in xfiles:
            # normalize pathname for correct extraction out of tarball
            while xfile.startswith('./'): xfile = xfile[2:]
            dist.extract(fileprefix+xfile, self._tmpdir)
            xfilefull = os.path.join(self._tmpdir, xfile)
            newfilefull = os.path.join(self._tmpdir, newname)
            # since extraction is with pathname, move to new location
            if os.path.realpath(xfilefull) != os.path.realpath(newfilefull):
                os.rename(xfilefull, newfilefull)
                try:
                    os.removedirs(os.path.dirname(xfilefull))
                except OSError:
                    pass
        dist.close()

    def __del__(self):
        '''Cleanup any temporary files and close connection'''
        Connection.__del__(self)
        if self._tmpdir:
            self.__remove_if_tmp(self._certificate)
            self.__remove_if_tmp(self._privateKey)
            self.__remove_if_tmp(self._caChain)
            os.rmdir(self._tmpdir)
            self._tmpdir = None

    def __remove_if_tmp(self, filename):
        '''remove a filename from the tempdir, if it is in there''' 
        if not os.path.exists(filename): return
        if os.path.realpath(os.path.dirname(filename)) == \
           os.path.realpath(self._tmpdir):
            os.remove(filename)

    def setApplications(self, apps):
        '''set the applications supported; no more than getter/setter right now.'''
        self._apps = apps

    def getApplications(self):
        '''return the applications supported'''
        return self._apps

    def connect(self):
        '''connect to project server and register resource'''
        Connection.connect(self)
        if not self._sessionId:
            self._signup()

    def requestWork(self, application, start = None, limit = None):
        '''request list of work from project server, also obtains job locks'''
        if not self._connection: self.connect()
        args = { 'project': self._project, 'session_id': self._sessionId }
        args['application'] = application
        if start: args['start'] = limit
        if limit: args['limit'] = limit
        ret = self._postToServer("/resources/resource_request_work.php", args)
        ret = ret['LGI']['response']
        if not 'job' in ret: ret['job'] = []
        if not isinstance(ret['job'], list): ret['job'] = [ ret['job'] ]
        return ret

    def lockJob(self, jobId):
        '''Lock a job'''
        if not self._connection: self.connect()
        ret = self._postToServer("/resources/resource_lock_job.php", {
            'project': self._project, 'session_id': self._sessionId, 'job_id': jobId })
        return ret['LGI']['response']

    def unlockJob(self, jobId):
        '''Unlock a job'''
        if not self._connection: self.connect()
        ret = self._postToServer("/resources/resource_unlock_job.php", {
            'project': self._project, 'session_id': self._sessionId, 'job_id': jobId })
        return ret['LGI']['response']

    def jobState(self, jobId):
        '''Request the job status of a job'''
        if not self._connection: self.connect()
        ret = self._postToServer("/resources/resource_job_state.php", {
            'project': self._project, 'session_id': self._sessionId, 'job_id': jobId })
        return ret['LGI']['response']
    
    def close(self):
        '''Signoff resource and close connection'''
        if self._sessionId:
            self._signoff()
        Connection.close(self)

    def _signup(self):
        '''signup resource with server
        @return sessionid obtained'''
        ret = self._postToServer("/resources/resource_signup_resource.php", { 'project': self._project })
        self._sessionId = ret['LGI']['response']['session_id']
        return ret

    def _signoff(self):
        '''signoff resource from server'''
        ret = self._postToServer("/resources/resource_signoff_resource.php", {
            'project': self._project, 'session_id': self._sessionId })
        self._sessionId = None
        return ret


# test program
if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.stderr.write('LGI Resource API testing program\n')
        sys.stderr.write('Usage: %s <path to LGI.cfg>\n'%sys.argv[0])
        sys.exit(1)

    print('Testing LGI Resource API')
    resource = Resource(sys.argv[1])
    for app in resource.getApplications():
        print('* Application "%s"'%(app))
        print('  - requesting work')
        response = resource.requestWork(app)
        if not 'job' in response or not response['job']:
            print('    > no jobs to be run, for more testing submit a job first')
        else:
            jobs = response['job']
            if not isinstance(jobs, list): jobs = [jobs]
            print('    > %d jobs pending, unlocking them again'%(len(jobs)))
            for job in jobs: resource.unlockJob(job['job_id'])
            print('  - retrieving info of job %d'%(jobs[0]['job_id']))
            response = resource.jobState(jobs[0]['job_id'])
            print('    > state=%s'%(response['job']['state']))
    

# vim:ts=4:sw=4:expandtab:
