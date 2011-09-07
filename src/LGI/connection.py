#
# Copyright (C) 2011 W. van Engen, Stichting FOM, The Netherlands
# Copyright (C) 2010 M.F. Somers, Theoretical Chemistry Group, Leiden University
#
# This is free software; you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation.
#
# http://www.gnu.org/licenses/gpl.txt

import xml.dom.minidom
import xml2dict
# support Python2 and Python3
try: import urllib.parse as urlparse
except ImportError: import urlparse
try: import http.client as httplib
except ImportError: import httplib


class LGIException(Exception):
    '''Base LGI exception'''
    pass


class LGIServerException(LGIException):
    '''Server exception; with response property'''
    def __init__(self, msg, response):
        LGIException.__init__(self, msg)
        self.response = response


class Connection:
    '''Base class for communication with an LGI server. This takes care of
    authentication, posting variables and common xml parsing. Also includes
    access to the standard repository.'''

    '''Create a new LGI connection.

    @type url str
    @param url LGI project server's base url
    @type project str
    @param project LGI project name to work with
    @type certificate str
    @param certificate location of user certificate file
    @type privateKey str
    @param privateKey location of user private key file
    @type caChain str
    @param caChain location of CA chain to validate LGI project server with
    '''
    def __init__(self, url, project, certificate, privateKey, caChain):
        self._connection = None
        self._host = None
        self._url = url
        self._project = project
        self._certificate = certificate
        self._privateKey = privateKey
        self._caChain = caChain

    def connect(self):
        '''Connect to the LGI project server.

        Will be called before any other communication is done.

        @raise LGIException when base url is invalid
        '''
        if self._host is None:
            dURL = urlparse.urlparse(self._url)

            if dURL[0] != 'https': 
                raise LGIException("LGI project server must have a https url")
            else:
                # XXX still bails if username/password present
                if dURL[1].find(':') < 0:
                    self._host = dURL[1]
                    self._port = 443
                else:
                    (self._host, self._port) = dURL[1].split(':', 1)
                    self._port = int(self._port)
                self._path = dURL[2]
        if self._connection is None: 
            self._connection = _HTTPSConnection(self._host, port=self._port, privateKey=self._privateKey, certificate=self._certificate, caChain=self._caChain)
            self._connection.connect()

    def close(self):
        '''Close connection to LGI server, if any'''
        if self._connection:
            self._connection.close()
            self._connection = None

    def _postToServer(self, url, variables={}, files={}):
        '''Send a request to the LGI server.

        @type url str
        @param url to post, relative to base url or absolute when starting with "https:"
        @type variables dict(str)
        @param variables key->value pairs to POST
        @type files dict(dict(str))
        @param files files to upload key->(filename_sent,local_filename)
        @rtype dict
        @return Dictionary of parsed XML response
        @raise LGIServerException when the project server returned an error response
        '''
        if self._connection is None: self.connect()
        # relative to base url
        if not url.lower().startswith('https:'): url = self._url + url

        boundary = "@$_Th1s_1s_th3_b0und@ry_@$"
        data = []

        if variables:
            for key in variables:
                data.append("--" + boundary)
                data.append('Content-Disposition: form-data; name="%s"' % key)
                data.append("")
                data.append(str(variables[key]))

        if files:
            for key in files:
                data.append("--" + boundary)
                data.append('Content-Disposition: form-data; name="%s"; filename="%s"' % ( key, files[key][0] ))
                data.append("Content-Type: application/octet-stream")
                data.append("")
                data.append(files[key][1])
        data.append("--" + boundary + "--")
        data.append( "" );                

        body = "\r\n".join(data)
        headers = { "Content-type": "multipart/form-data; boundary=%s"%boundary,
                "Accept": "text/plain",
                "Connection": "keep-alive" }

        try:
            self._connection.request("POST", url, body, headers)
            response = self._connection.getresponse()
        except httplib.HTTPException:
            # silently reconnect if connection re-use comes to its limit
            # TODO use urllib2 for more intelligent retries
            self._connection.close()
            self._connection.connect()
            self._connection.request("POST", url, body, headers)
            response = self._connection.getresponse()
    
        rdata = response.read()
        resp = xml2dict.xml2dict(xml.dom.minidom.parseString(rdata))
        if 'LGI' in resp and 'response' in resp['LGI'] and 'error' in resp['LGI']['response']:
            error = resp['LGI']['response']['error']
            raise LGIServerException('LGI error %d: %s'%(error['number'], error['message']), resp)
        return resp

    def fileList(self, url):
        '''Return list of files in repository.
        @type url str
        @param url absolute repository location
        @rtype list(dict())
        @return list of properties of filenames
        '''
        if self._connection is None: self.connect()
        repourl, repodir, repoid = url.rsplit('/', 2)
        ret = self._postToServer(repourl + "/repository_content.php", {'repository': repoid})
        ret = ret['repository_content']
        if not 'file' in ret: ret['file'] = None
        if type(ret['file']) != list: ret['file'] = [ ret['file'] ]
        return ret['file']

    def fileDownload(self, url):
        '''Download a file from a repository.
        @type url str
        @param url absolute url of file
        @rtype str
        @return contents of the file
        '''
        try:
            self._connection.request("GET", url)
            response = self._connection.getresponse()
        except httplib.HTTPException:
            # silently reconnect if connection re-use comes to its limit
            # TODO use urllib2 for more intelligent retries
            self._connection.close()
            self._connection.connect()
            self._connection.request("GET", url)
            response = self._connection.getresponse()
        return response.read()

    def fileUpload(self, url, data):
        '''Upload a file to a repository.
        @type url str
        @param url destination location, repository with filename appended
        @type data str
        @param data file data to upload
        @rtype dict
        @return parsed server response
        @raise LGIServerException when the project server returned an error status
        '''
        try:
            self._connection.request("PUT", url, data)
            response = self._connection.getresponse()
        except httplib.HTTPException:
            # silently reconnect if connection re-use comes to its limit
            # TODO use urllib2 for more intelligent retries
            self._connection.close()
            self._connection.connect()
            self._connection.request("PUT", url, data)
            response = self._connection.getresponse()
        resp = xml2dict.xml2dict(xml.dom.minidom.parseString(response.read()))
        if 'status' in resp and 'number' in resp['status'] and int(resp['status']['number'])>=400:
            status=resp['status']
            raise LGIServerException('LGI error status %d: %s'%(status['number'], status['message']), resp)
        return resp

    def fileDelete(self, url):
        '''Remove a file from a repository.
        @type url str
        @param url location to remote, repository with filename appended
        @rtype dict
        @return parsed server response
        @raise LGIServerException when the project server returned an error status
        '''
        try:
            self._connection.request("DELETE", url)
            response = self._connection.getresponse()
        except httplib.HTTPException:
            # silently reconnect if connection re-use comes to its limit
            # TODO use urllib2 for more intelligent retries
            self._connection.close()
            self._connection.connect()
            self._connection.request("DELETE", url)
            response = self._connection.getresponse()
        resp = xml2dict.xml2dict(xml.dom.minidom.parseString(response.read()))
        if 'status' in resp and 'number' in resp['status'] and int(resp['status']['number'])>=400:
            status=resp['status']
            raise LGIServerException('LGI error status %d: %s'%(status['number'], status['message']), resp)
        return resp


# ssl only available from python 2.6 onwards
try:
    import socket
    import ssl

    class _HTTPSConnection(httplib.HTTPConnection):
        def __init__(self, host, port=443, privateKey=None, certificate=None, caChain=None, sslVersion=ssl.PROTOCOL_SSLv23, certificateRequired=ssl.CERT_REQUIRED, strict=None):
            httplib.HTTPConnection.__init__(self, host, port, strict)
            self._privateKey = privateKey
            self._certificate = certificate
            self._caChain = caChain
            self._sslVersion = sslVersion
            self._certificateRequired = certificateRequired

        def connect(self):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock = ssl.wrap_socket(sock, keyfile=self._privateKey, certfile=self._certificate, 
                                        ca_certs=self._caChain, ssl_version=self._sslVersion, cert_reqs=self._certificateRequired)
            self.sock.connect( (self.host, self.port) )

except ImportError:
    class _HTTPSConnection(httplib.HTTPSConnection):
        def __init__(self, host, port=443, privateKey=None, certificate=None, caChain=None, sslVersion=None, certificateRequired=None, strict=None):
            httplib.HTTPSConnection.__init__(self, host, port, privateKey, certificate, strict)

# vim:ts=4:sw=4:expandtab:
