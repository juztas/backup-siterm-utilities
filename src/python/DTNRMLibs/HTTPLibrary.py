#!/usr/bin/env python
"""
HTTP library for HTTP(s) communication

Copyright 2017 California Institute of Technology
   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at
       http://www.apache.org/licenses/LICENSE-2.0
   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
Title 			: dtnrm
Author			: Justas Balcas
Email 			: justas.balcas (at) cern.ch
@Copyright		: Copyright (C) 2016 California Institute of Technology
Date			: 2017/09/26
"""
import base64
import urlparse
import urllib
from DTNRMLibs.pycurl_manager import RequestHandler
from DTNRMLibs.CustomExceptions import ValidityFailure

def argValidity(arg, aType):
    """ Argument validation """
    if not arg:
        return {} if aType == dict else []
    if aType == dict:
        if isinstance(arg, dict):
            return arg
    elif aType == list:
        if isinstance(arg, list):
            return arg
    else:
        raise ValidityFailure("Input %s != %s." % (type(arg), aType))


def check_server_url(url):
    """Check if given url starts with http tag"""
    goodName = url.startswith('http://') or url.startswith('https://')
    if not goodName:
        msg = "You must include http(s):// in your server's address, %s doesn't" % url
        raise ValueError(msg)


def sanitizeURL(url):
    """Take the url with/without username and password and return sanitized url,
       username and password in dict format
       ':' is not supported in username or password.
    """
    endpointComponents = urlparse.urlparse(url)
    if endpointComponents.port:
        netloc = '%s:%s' % (endpointComponents.hostname,
                            endpointComponents.port)
    else:
        netloc = endpointComponents.hostname
    url = urlparse.urlunparse(
        [endpointComponents.scheme,
         netloc,
         endpointComponents.path,
         endpointComponents.params,
         endpointComponents.query,
         endpointComponents.fragment])

    return {'url': url, 'username': endpointComponents.username,
            'password': endpointComponents.password}


def encodeRequest(configreq, listParams=None):
    """ Used to encode the request from a dict to a string.
    Include the code needed for transforming lists in the format
    required by the server.
    """
    if not listParams:
        listParams = []
    encodedLists = ''
    for lparam in listParams:
        if lparam in configreq:
            if len(configreq[lparam]) > 0:
                encodedLists += ('&%s=' % lparam) + ('&%s=' % lparam).join(map(urllib.quote, configreq[lparam]))
            del configreq[lparam]
    encoded = urllib.urlencode(configreq) + encodedLists
    return str(encoded)


class Requests(dict):
    """Make any type of HTTP(s) request"""
    def __init__(self, url='http://localhost', inputdict=None):
        if not inputdict:
            inputdict = {}
        # set up defaults
        self.setdefault("accept_type", 'application/json')
        self.setdefault("content_type", ' application/json')
        self.additionalHeaders = {}

        self.reqmgr = RequestHandler()
        # check for basic auth early, as if found this changes the url
        urlComponent = sanitizeURL(url)
        if urlComponent['username'] is not None:
            self.addBasicAuth(urlComponent['username'], urlComponent['password'])
            url = urlComponent['url']  # remove user, password from url

        self.setdefault("host", url)
        self.update(inputdict)
        self['endpoint_components'] = urlparse.urlparse(self['host'])

        check_server_url(self['host'])

    def addBasicAuth(self, username, password):
        """Add basic auth headers to request if user/pass is used"""
        authString = "Basic %s" % base64.encodestring('%s:%s' % (
            username, password)).strip()
        self.additionalHeaders["Authorization"] = authString

    def get(self, uri=None, data=None, incoming_headers=None,
            encode=True, decode=True, contentType=None):
        """
        GET some data
        """
        incoming_headers = argValidity(incoming_headers, dict)
        return self.makeRequest(uri, data, 'GET', incoming_headers,
                                encode, decode, contentType)

    def post(self, uri=None, data=None, incoming_headers=None,
             encode=True, decode=True, contentType=None):
        """
        POST some data
        """
        incoming_headers = argValidity(incoming_headers, dict)
        return self.makeRequest(uri, data, 'POST', incoming_headers,
                                encode, decode, contentType)

    def put(self, uri=None, data=None, incoming_headers=None,
            encode=True, decode=True, contentType=None):
        """
        PUT some data
        """
        incoming_headers = argValidity(incoming_headers, dict)
        return self.makeRequest(uri, data, 'PUT', incoming_headers,
                                encode, decode, contentType)

    def delete(self, uri=None, data=None, incoming_headers=None,
               encode=True, decode=True, contentType=None):
        """
        DELETE some data
        """
        incoming_headers = argValidity(incoming_headers, dict)
        return self.makeRequest(uri, data, 'DELETE', incoming_headers,
                                encode, decode, contentType)

    def makeRequest(self, uri=None, data=None, verb='GET', incoming_headers=None,
                    encoder=True, decoder=True, contentType=None):
        """
        Make HTTP(s) request via pycurl library. Stay complaint with
        makeRequest_httplib method.
        """
        del encoder
        incoming_headers = argValidity(incoming_headers, dict)
        # ckey, cert = self.getKeyCert()
        # capath = self.getCAPath()
        if not contentType:
            contentType = self['content_type']
        headers = {"Content-type": contentType,
                   "User-agent": "DTN-RM",
                   "Accept": self['accept_type']}
        for key, value in self.additionalHeaders.items():
            headers[key] = value
        # And now overwrite any headers that have been passed into the call:
        headers.update(incoming_headers)
        url = self['host'] + uri
        response, data = self.reqmgr.request(url, data, headers, verb=verb,
                                             ckey=None, cert=None, capath=None, decode=decoder)
        return data, response.status, response.reason, response.fromcache
