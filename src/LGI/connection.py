#
# Copyright (C) 2011 W. van Engen, Stichting FOM, The Netherlands
# Copyright (C) 2010 M.F. Somers, Theoretical Chemistry Group, Leiden University
#
# This is free software; you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation.
#
# http://www.gnu.org/licenses/gpl.txt

import sys
import xml.dom.minidom
import xml2dict
# support Python2 and Python3
try: import urllib.parse as urlparse
except ImportError: import urlparse
try: import http.client as httplib
except ImportError: import httplib

class LGIException(Exception):
    pass

class Connection:
    '''Base class for communication to an LGI server. This takes care of
    authentication, posting variables and common xml parsing.'''

    def __init__(self, url, project, certificate, privateKey, caChain):
        self._connection = None
        self._host = None
        self._url = url
        self._project = project
        self._certificate = certificate
        self._privateKey = privateKey
        self._caChain = caChain

    def connect(self):
        '''Connect to the LGI project server. Must be called before
        any other communication is done.'''
        if not self._host:
            dURL = urlparse.urlparse(self._url)

            if dURL[0] != 'https': 
                raise LGIException("LGI project server must have a https url")
            else:
                # XXX still bails if username/password present
                if dURL[1].find(':') < 0:
                    self._host = dURL[1]
                    self._port = None
                else:
                    (self._host, self._port) = dURL[1].split(':', 1)
                    self._port = int(self._port)
                self._path = dURL[2]
        if not self._connection: 
            self._connection = _HTTPSConnection(self._host, port=self._port, privateKey=self._privateKey, certificate=self._certificate, caChain=self._caChain)
            self._connection.connect()

    def close(self):
        '''Close connection to LGI server, if any'''
        if self._connection:
            self._connection.close()
            self._connection = None

    def __del__(self):
        '''Upon deletion of object, close connection automatically.'''
        self.close()
    
    def _postToServer(self, apipath, variables={}, files={}, path=None):
        '''Send a request to the LGI server'''
        if not self._connection: self.connect()

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

        if path is None: path = self._path + apipath
        try:
            self._connection.request("POST", path, body, headers)
            response = self._connection.getresponse()
        except httplib.HTTPException:
            # silently reconnect if connection re-use comes to its limit
            # TODO use urllib2 for more intelligent retries
            self._connection.close()
            self._connection.connect()
            self._connection.request("POST", path, body, headers)
            response = self._connection.getresponse()
    
        rdata = response.read()
        return xml2dict.xml2dict(xml.dom.minidom.parseString(rdata))


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
