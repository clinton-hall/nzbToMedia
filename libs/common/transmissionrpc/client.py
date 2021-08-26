# -*- coding: utf-8 -*-
# Copyright (c) 2008-2013 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

import re, time, operator, warnings, os
import base64
import json

from transmissionrpc.constants import DEFAULT_PORT, DEFAULT_TIMEOUT
from transmissionrpc.error import TransmissionError, HTTPHandlerError
from transmissionrpc.utils import LOGGER, get_arguments, make_rpc_name, argument_value_convert, rpc_bool
from transmissionrpc.httphandler import DefaultHTTPHandler
from transmissionrpc.torrent import Torrent
from transmissionrpc.session import Session

from six import PY3, integer_types, string_types, iteritems

if PY3:
    from urllib.parse import urlparse
    from urllib.request import urlopen
else:
    from urlparse import urlparse
    from urllib2 import urlopen

def debug_httperror(error):
    """
    Log the Transmission RPC HTTP error.
    """
    try:
        data = json.loads(error.data)
    except ValueError:
        data = error.data
    LOGGER.debug(
        json.dumps(
            {
                'response': {
                    'url': error.url,
                    'code': error.code,
                    'msg': error.message,
                    'headers': error.headers,
                    'data': data,
                }
            },
            indent=2
        )
    )

def parse_torrent_id(arg):
    """Parse an torrent id or torrent hashString."""
    torrent_id = None
    if isinstance(arg, integer_types):
        # handle index
        torrent_id = int(arg)
    elif isinstance(arg, float):
        torrent_id = int(arg)
        if torrent_id != arg:
            torrent_id = None
    elif isinstance(arg, string_types):
        try:
            torrent_id = int(arg)
            if torrent_id >= 2**31:
                torrent_id = None
        except (ValueError, TypeError):
            pass
        if torrent_id is None:
            # handle hashes
            try:
                int(arg, 16)
                torrent_id = arg
            except (ValueError, TypeError):
                pass
    return torrent_id

def parse_torrent_ids(args):
    """
    Take things and make them valid torrent identifiers
    """
    ids = []

    if args is None:
        pass
    elif isinstance(args, string_types):
        for item in re.split('[ ,]+', args):
            if len(item) == 0:
                continue
            addition = None
            torrent_id = parse_torrent_id(item)
            if torrent_id is not None:
                addition = [torrent_id]
            if not addition:
                # handle index ranges i.e. 5:10
                match = re.match('^(\d+):(\d+)$', item)
                if match:
                    try:
                        idx_from = int(match.group(1))
                        idx_to = int(match.group(2))
                        addition = list(range(idx_from, idx_to + 1))
                    except ValueError:
                        pass
            if not addition:
                raise ValueError('Invalid torrent id, \"%s\"' % item)
            ids.extend(addition)
    elif isinstance(args, (list, tuple)):
        for item in args:
            ids.extend(parse_torrent_ids(item))
    else:
        torrent_id = parse_torrent_id(args)
        if torrent_id == None:
            raise ValueError('Invalid torrent id')
        else:
            ids = [torrent_id]
    return ids

"""
Torrent ids

Many functions in Client takes torrent id. A torrent id can either be id or
hashString. When supplying multiple id's it is possible to use a list mixed
with both id and hashString.

Timeouts

Since most methods results in HTTP requests against Transmission, it is
possible to provide a argument called ``timeout``. Timeout is only effective
when using Python 2.6 or later and the default timeout is 30 seconds.
"""

class Client(object):
    """
    Client is the class handling the Transmission JSON-RPC client protocol.
    """

    def __init__(self, address='localhost', port=DEFAULT_PORT, user=None, password=None, http_handler=None, timeout=None):
        if isinstance(timeout, (integer_types, float)):
            self._query_timeout = float(timeout)
        else:
            self._query_timeout = DEFAULT_TIMEOUT
        urlo = urlparse(address)
        if urlo.scheme == '':
            base_url = 'http://' + address + ':' + str(port)
            self.url = base_url + '/transmission/rpc'
        else:
            if urlo.port:
                self.url = urlo.scheme + '://' + urlo.hostname + ':' + str(urlo.port) + urlo.path
            else:
                self.url = urlo.scheme + '://' + urlo.hostname + urlo.path
            LOGGER.info('Using custom URL "' + self.url + '".')
            if urlo.username and urlo.password:
                user = urlo.username
                password = urlo.password
            elif urlo.username or urlo.password:
                LOGGER.warning('Either user or password missing, not using authentication.')
        if http_handler is None:
            self.http_handler = DefaultHTTPHandler()
        else:
            if hasattr(http_handler, 'set_authentication') and hasattr(http_handler, 'request'):
                self.http_handler = http_handler
            else:
                raise ValueError('Invalid HTTP handler.')
        if user and password:
            self.http_handler.set_authentication(self.url, user, password)
        elif user or password:
            LOGGER.warning('Either user or password missing, not using authentication.')
        self._sequence = 0
        self.session = None
        self.session_id = 0
        self.server_version = None
        self.protocol_version = None
        self.get_session()
        self.torrent_get_arguments = get_arguments('torrent-get'
                                                   , self.rpc_version)

    def _get_timeout(self):
        """
        Get current timeout for HTTP queries.
        """
        return self._query_timeout

    def _set_timeout(self, value):
        """
        Set timeout for HTTP queries.
        """
        self._query_timeout = float(value)

    def _del_timeout(self):
        """
        Reset the HTTP query timeout to the default.
        """
        self._query_timeout = DEFAULT_TIMEOUT

    timeout = property(_get_timeout, _set_timeout, _del_timeout, doc="HTTP query timeout.")

    def _http_query(self, query, timeout=None):
        """
        Query Transmission through HTTP.
        """
        headers = {'x-transmission-session-id': str(self.session_id)}
        result = {}
        request_count = 0
        if timeout is None:
            timeout = self._query_timeout
        while True:
            LOGGER.debug(json.dumps({'url': self.url, 'headers': headers, 'query': query, 'timeout': timeout}, indent=2))
            try:
                result = self.http_handler.request(self.url, query, headers, timeout)
                break
            except HTTPHandlerError as error:
                if error.code == 409:
                    LOGGER.info('Server responded with 409, trying to set session-id.')
                    if request_count > 1:
                        raise TransmissionError('Session ID negotiation failed.', error)
                    session_id = None
                    for key in list(error.headers.keys()):
                        if key.lower() == 'x-transmission-session-id':
                            session_id = error.headers[key]
                            self.session_id = session_id
                            headers = {'x-transmission-session-id': str(self.session_id)}
                    if session_id is None:
                        debug_httperror(error)
                        raise TransmissionError('Unknown conflict.', error)
                else:
                    debug_httperror(error)
                    raise TransmissionError('Request failed.', error)
            request_count += 1
        return result

    def _request(self, method, arguments=None, ids=None, require_ids=False, timeout=None):
        """
        Send json-rpc request to Transmission using http POST
        """
        if not isinstance(method, string_types):
            raise ValueError('request takes method as string')
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise ValueError('request takes arguments as dict')
        ids = parse_torrent_ids(ids)
        if len(ids) > 0:
            arguments['ids'] = ids
        elif require_ids:
            raise ValueError('request require ids')

        query = json.dumps({'tag': self._sequence, 'method': method
                            , 'arguments': arguments})
        self._sequence += 1
        start = time.time()
        http_data = self._http_query(query, timeout)
        elapsed = time.time() - start
        LOGGER.info('http request took %.3f s' % (elapsed))

        try:
            data = json.loads(http_data)
        except ValueError as error:
            LOGGER.error('Error: ' + str(error))
            LOGGER.error('Request: \"%s\"' % (query))
            LOGGER.error('HTTP data: \"%s\"' % (http_data))
            raise

        LOGGER.debug(json.dumps(data, indent=2))
        if 'result' in data:
            if data['result'] != 'success':
                raise TransmissionError('Query failed with result \"%s\".' % (data['result']))
        else:
            raise TransmissionError('Query failed without result.')

        results = {}
        if method == 'torrent-get':
            for item in data['arguments']['torrents']:
                results[item['id']] = Torrent(self, item)
                if self.protocol_version == 2 and 'peers' not in item:
                    self.protocol_version = 1
        elif method == 'torrent-add':
            item = None
            if 'torrent-added' in data['arguments']:
                item = data['arguments']['torrent-added']
            elif 'torrent-duplicate' in data['arguments']:
                item = data['arguments']['torrent-duplicate']
            if item:
                results[item['id']] = Torrent(self, item)
            else:
                raise TransmissionError('Invalid torrent-add response.')
        elif method == 'session-get':
            self._update_session(data['arguments'])
        elif method == 'session-stats':
            # older versions of T has the return data in "session-stats"
            if 'session-stats' in data['arguments']:
                self._update_session(data['arguments']['session-stats'])
            else:
                self._update_session(data['arguments'])
        elif method in ('port-test', 'blocklist-update', 'free-space', 'torrent-rename-path'):
            results = data['arguments']
        else:
            return None

        return results

    def _update_session(self, data):
        """
        Update session data.
        """
        if self.session:
            self.session.from_request(data)
        else:
            self.session = Session(self, data)

    def _update_server_version(self):
        """Decode the Transmission version string, if available."""
        if self.server_version is None:
            version_major = 1
            version_minor = 30
            version_changeset = 0
            version_parser = re.compile('(\d).(\d+) \((\d+)\)')
            if hasattr(self.session, 'version'):
                match = version_parser.match(self.session.version)
                if match:
                    version_major = int(match.group(1))
                    version_minor = int(match.group(2))
                    version_changeset = match.group(3)
            self.server_version = (version_major, version_minor, version_changeset)

    @property
    def rpc_version(self):
        """
        Get the Transmission RPC version. Trying to deduct if the server don't have a version value.
        """
        if self.protocol_version is None:
            # Ugly fix for 2.20 - 2.22 reporting rpc-version 11, but having new arguments
            if self.server_version and (self.server_version[0] == 2 and self.server_version[1] in [20, 21, 22]):
                self.protocol_version = 12
            # Ugly fix for 2.12 reporting rpc-version 10, but having new arguments
            elif self.server_version and (self.server_version[0] == 2 and self.server_version[1] == 12):
                self.protocol_version = 11
            elif hasattr(self.session, 'rpc_version'):
                self.protocol_version = self.session.rpc_version
            elif hasattr(self.session, 'version'):
                self.protocol_version = 3
            else:
                self.protocol_version = 2
        return self.protocol_version

    def _rpc_version_warning(self, version):
        """
        Add a warning to the log if the Transmission RPC version is lower then the provided version.
        """
        if self.rpc_version < version:
            LOGGER.warning('Using feature not supported by server. RPC version for server %d, feature introduced in %d.'
                % (self.rpc_version, version))

    def add_torrent(self, torrent, timeout=None, **kwargs):
        """
        Add torrent to transfers list. Takes a uri to a torrent or base64 encoded torrent data in ``torrent``.
        Additional arguments are:

        ===================== ===== =========== =============================================================
        Argument              RPC   Replaced by Description
        ===================== ===== =========== =============================================================
        ``bandwidthPriority`` 8 -               Priority for this transfer.
        ``cookies``           13 -              One or more HTTP cookie(s).
        ``download_dir``      1 -               The directory where the downloaded contents will be saved in.
        ``files_unwanted``    1 -               A list of file id's that shouldn't be downloaded.
        ``files_wanted``      1 -               A list of file id's that should be downloaded.
        ``paused``            1 -               If True, does not start the transfer when added.
        ``peer_limit``        1 -               Maximum number of peers allowed.
        ``priority_high``     1 -               A list of file id's that should have high priority.
        ``priority_low``      1 -               A list of file id's that should have low priority.
        ``priority_normal``   1 -               A list of file id's that should have normal priority.
        ===================== ===== =========== =============================================================

        Returns a Torrent object with the fields.
        """
        if torrent is None:
            raise ValueError('add_torrent requires data or a URI.')
        torrent_data = None
        parsed_uri = urlparse(torrent)
        if parsed_uri.scheme in ['ftp', 'ftps', 'http', 'https']:
            # there has been some problem with T's built in torrent fetcher,
            # use a python one instead
            torrent_file = urlopen(torrent)
            torrent_data = torrent_file.read()
            torrent_data = base64.b64encode(torrent_data).decode('utf-8')
        if parsed_uri.scheme in ['file']:
            filepath = torrent
            # uri decoded different on linux / windows ?
            if len(parsed_uri.path) > 0:
                filepath = parsed_uri.path
            elif len(parsed_uri.netloc) > 0:
                filepath = parsed_uri.netloc
            torrent_file = open(filepath, 'rb')
            torrent_data = torrent_file.read()
            torrent_data = base64.b64encode(torrent_data).decode('utf-8')
        if not torrent_data:
            if torrent.endswith('.torrent') or torrent.startswith('magnet:'):
                torrent_data = None
            else:
                might_be_base64 = False
                try:
                    # check if this is base64 data
                    if PY3:
                        base64.b64decode(torrent.encode('utf-8'))
                    else:
                        base64.b64decode(torrent)
                    might_be_base64 = True
                except Exception:
                    pass
                if might_be_base64:
                    torrent_data = torrent
        args = {}
        if torrent_data:
            args = {'metainfo': torrent_data}
        else:
            args = {'filename': torrent}
        for key, value in iteritems(kwargs):
            argument = make_rpc_name(key)
            (arg, val) = argument_value_convert('torrent-add', argument, value, self.rpc_version)
            args[arg] = val
        return list(self._request('torrent-add', args, timeout=timeout).values())[0]

    def add(self, data, timeout=None, **kwargs):
        """

        .. WARNING::
            Deprecated, please use add_torrent.
        """
        args = {}
        if data:
            args = {'metainfo': data}
        elif 'metainfo' not in kwargs and 'filename' not in kwargs:
            raise ValueError('No torrent data or torrent uri.')
        for key, value in iteritems(kwargs):
            argument = make_rpc_name(key)
            (arg, val) = argument_value_convert('torrent-add', argument, value, self.rpc_version)
            args[arg] = val
        warnings.warn('add has been deprecated, please use add_torrent instead.', DeprecationWarning)
        return self._request('torrent-add', args, timeout=timeout)

    def add_uri(self, uri, **kwargs):
        """

        .. WARNING::
            Deprecated, please use add_torrent.
        """
        if uri is None:
            raise ValueError('add_uri requires a URI.')
        # there has been some problem with T's built in torrent fetcher,
        # use a python one instead
        parsed_uri = urlparse(uri)
        torrent_data = None
        if parsed_uri.scheme in ['ftp', 'ftps', 'http', 'https']:
            torrent_file = urlopen(uri)
            torrent_data = torrent_file.read()
            torrent_data = base64.b64encode(torrent_data).decode('utf-8')
        if parsed_uri.scheme in ['file']:
            filepath = uri
            # uri decoded different on linux / windows ?
            if len(parsed_uri.path) > 0:
                filepath = parsed_uri.path
            elif len(parsed_uri.netloc) > 0:
                filepath = parsed_uri.netloc
            torrent_file = open(filepath, 'rb')
            torrent_data = torrent_file.read()
            torrent_data = base64.b64encode(torrent_data).decode('utf-8')
        warnings.warn('add_uri has been deprecated, please use add_torrent instead.', DeprecationWarning)
        if torrent_data:
            return self.add(torrent_data, **kwargs)
        else:
            return self.add(None, filename=uri, **kwargs)

    def remove_torrent(self, ids, delete_data=False, timeout=None):
        """
        remove torrent(s) with provided id(s). Local data is removed if
        delete_data is True, otherwise not.
        """
        self._rpc_version_warning(3)
        self._request('torrent-remove',
                    {'delete-local-data':rpc_bool(delete_data)}, ids, True, timeout=timeout)

    def remove(self, ids, delete_data=False, timeout=None):
        """

        .. WARNING::
            Deprecated, please use remove_torrent.
        """
        warnings.warn('remove has been deprecated, please use remove_torrent instead.', DeprecationWarning)
        self.remove_torrent(ids, delete_data, timeout)

    def start_torrent(self, ids, bypass_queue=False, timeout=None):
        """Start torrent(s) with provided id(s)"""
        method = 'torrent-start'
        if bypass_queue and self.rpc_version >= 14:
            method = 'torrent-start-now'
        self._request(method, {}, ids, True, timeout=timeout)

    def start(self, ids, bypass_queue=False, timeout=None):
        """

        .. WARNING::
            Deprecated, please use start_torrent.
        """
        warnings.warn('start has been deprecated, please use start_torrent instead.', DeprecationWarning)
        self.start_torrent(ids, bypass_queue, timeout)

    def start_all(self, bypass_queue=False, timeout=None):
        """Start all torrents respecting the queue order"""
        torrent_list = self.get_torrents()
        method = 'torrent-start'
        if self.rpc_version >= 14:
            if bypass_queue:
                method = 'torrent-start-now'
            torrent_list = sorted(torrent_list, key=operator.attrgetter('queuePosition'))
        ids = [x.id for x in torrent_list]
        self._request(method, {}, ids, True, timeout=timeout)

    def stop_torrent(self, ids, timeout=None):
        """stop torrent(s) with provided id(s)"""
        self._request('torrent-stop', {}, ids, True, timeout=timeout)

    def stop(self, ids, timeout=None):
        """

        .. WARNING::
            Deprecated, please use stop_torrent.
        """
        warnings.warn('stop has been deprecated, please use stop_torrent instead.', DeprecationWarning)
        self.stop_torrent(ids, timeout)

    def verify_torrent(self, ids, timeout=None):
        """verify torrent(s) with provided id(s)"""
        self._request('torrent-verify', {}, ids, True, timeout=timeout)

    def verify(self, ids, timeout=None):
        """

        .. WARNING::
            Deprecated, please use verify_torrent.
        """
        warnings.warn('verify has been deprecated, please use verify_torrent instead.', DeprecationWarning)
        self.verify_torrent(ids, timeout)

    def reannounce_torrent(self, ids, timeout=None):
        """Reannounce torrent(s) with provided id(s)"""
        self._rpc_version_warning(5)
        self._request('torrent-reannounce', {}, ids, True, timeout=timeout)

    def reannounce(self, ids, timeout=None):
        """

        .. WARNING::
            Deprecated, please use reannounce_torrent.
        """
        warnings.warn('reannounce has been deprecated, please use reannounce_torrent instead.', DeprecationWarning)
        self.reannounce_torrent(ids, timeout)

    def get_torrent(self, torrent_id, arguments=None, timeout=None):
        """
        Get information for torrent with provided id.
        ``arguments`` contains a list of field names to be returned, when None
        all fields are requested. See the Torrent class for more information.

        Returns a Torrent object with the requested fields.
        """
        if not arguments:
            arguments = self.torrent_get_arguments
        torrent_id = parse_torrent_id(torrent_id)
        if torrent_id is None:
            raise ValueError("Invalid id")
        result = self._request('torrent-get', {'fields': arguments}, torrent_id, require_ids=True, timeout=timeout)
        if torrent_id in result:
            return result[torrent_id]
        else:
            for torrent in result.values():
                if torrent.hashString == torrent_id:
                    return torrent
            raise KeyError("Torrent not found in result")

    def get_torrents(self, ids=None, arguments=None, timeout=None):
        """
        Get information for torrents with provided ids. For more information see get_torrent.

        Returns a list of Torrent object.
        """
        if not arguments:
            arguments = self.torrent_get_arguments
        return list(self._request('torrent-get', {'fields': arguments}, ids, timeout=timeout).values())

    def info(self, ids=None, arguments=None, timeout=None):
        """

        .. WARNING::
            Deprecated, please use get_torrent or get_torrents. Please note that the return argument has changed in
            the new methods. info returns a dictionary indexed by torrent id.
        """
        warnings.warn('info has been deprecated, please use get_torrent or get_torrents instead.', DeprecationWarning)
        if not arguments:
            arguments = self.torrent_get_arguments
        return self._request('torrent-get', {'fields': arguments}, ids, timeout=timeout)

    def list(self, timeout=None):
        """

        .. WARNING::
            Deprecated, please use get_torrent or get_torrents. Please note that the return argument has changed in
            the new methods. list returns a dictionary indexed by torrent id.
        """
        warnings.warn('list has been deprecated, please use get_torrent or get_torrents instead.', DeprecationWarning)
        fields = ['id', 'hashString', 'name', 'sizeWhenDone', 'leftUntilDone'
            , 'eta', 'status', 'rateUpload', 'rateDownload', 'uploadedEver'
            , 'downloadedEver', 'uploadRatio', 'queuePosition']
        return self._request('torrent-get', {'fields': fields}, timeout=timeout)

    def get_files(self, ids=None, timeout=None):
        """
    	Get list of files for provided torrent id(s). If ids is empty,
    	information for all torrents are fetched. This function returns a dictionary
    	for each requested torrent id holding the information about the files.

    	::

    		{
    			<torrent id>: {
    				<file id>: {
    					'name': <file name>,
    					'size': <file size in bytes>,
    					'completed': <bytes completed>,
    					'priority': <priority ('high'|'normal'|'low')>,
    					'selected': <selected for download (True|False)>
    				}

    				...
    			}

    			...
    		}
        """
        fields = ['id', 'name', 'hashString', 'files', 'priorities', 'wanted']
        request_result = self._request('torrent-get', {'fields': fields}, ids, timeout=timeout)
        result = {}
        for tid, torrent in iteritems(request_result):
            result[tid] = torrent.files()
        return result

    def set_files(self, items, timeout=None):
        """
        Set file properties. Takes a dictionary with similar contents as the result
    	of `get_files`.

    	::

    		{
    			<torrent id>: {
    				<file id>: {
    					'priority': <priority ('high'|'normal'|'low')>,
    					'selected': <selected for download (True|False)>
    				}

    				...
    			}

    			...
    		}
        """
        if not isinstance(items, dict):
            raise ValueError('Invalid file description')
        for tid, files in iteritems(items):
            if not isinstance(files, dict):
                continue
            wanted = []
            unwanted = []
            high = []
            normal = []
            low = []
            for fid, file_desc in iteritems(files):
                if not isinstance(file_desc, dict):
                    continue
                if 'selected' in file_desc and file_desc['selected']:
                    wanted.append(fid)
                else:
                    unwanted.append(fid)
                if 'priority' in file_desc:
                    if file_desc['priority'] == 'high':
                        high.append(fid)
                    elif file_desc['priority'] == 'normal':
                        normal.append(fid)
                    elif file_desc['priority'] == 'low':
                        low.append(fid)
            args = {
                'timeout': timeout
            }
            if len(high) > 0:
                args['priority_high'] = high
            if len(normal) > 0:
                args['priority_normal'] = normal
            if len(low) > 0:
                args['priority_low'] = low
            if len(wanted) > 0:
                args['files_wanted'] = wanted
            if len(unwanted) > 0:
                args['files_unwanted'] = unwanted
            self.change_torrent([tid], **args)

    def change_torrent(self, ids, timeout=None, **kwargs):
        """
    	Change torrent parameters for the torrent(s) with the supplied id's. The
    	parameters are:

        ============================ ===== =============== =======================================================================================
        Argument                     RPC   Replaced by     Description
        ============================ ===== =============== =======================================================================================
        ``bandwidthPriority``        5 -                   Priority for this transfer.
        ``downloadLimit``            5 -                   Set the speed limit for download in Kib/s.
        ``downloadLimited``          5 -                   Enable download speed limiter.
        ``files_unwanted``           1 -                   A list of file id's that shouldn't be downloaded.
        ``files_wanted``             1 -                   A list of file id's that should be downloaded.
        ``honorsSessionLimits``      5 -                   Enables or disables the transfer to honour the upload limit set in the session.
        ``location``                 1 -                   Local download location.
        ``peer_limit``               1 -                   The peer limit for the torrents.
        ``priority_high``            1 -                   A list of file id's that should have high priority.
        ``priority_low``             1 -                   A list of file id's that should have normal priority.
        ``priority_normal``          1 -                   A list of file id's that should have low priority.
        ``queuePosition``            14 -                  Position of this transfer in its queue.
        ``seedIdleLimit``            10 -                  Seed inactivity limit in minutes.
        ``seedIdleMode``             10 -                  Seed inactivity mode. 0 = Use session limit, 1 = Use transfer limit, 2 = Disable limit.
        ``seedRatioLimit``           5 -                   Seeding ratio.
        ``seedRatioMode``            5 -                   Which ratio to use. 0 = Use session limit, 1 = Use transfer limit, 2 = Disable limit.
        ``speed_limit_down``         1 - 5 downloadLimit   Set the speed limit for download in Kib/s.
        ``speed_limit_down_enabled`` 1 - 5 downloadLimited Enable download speed limiter.
        ``speed_limit_up``           1 - 5 uploadLimit     Set the speed limit for upload in Kib/s.
        ``speed_limit_up_enabled``   1 - 5 uploadLimited   Enable upload speed limiter.
        ``trackerAdd``               10 -                  Array of string with announce URLs to add.
        ``trackerRemove``            10 -                  Array of ids of trackers to remove.
        ``trackerReplace``           10 -                  Array of (id, url) tuples where the announce URL should be replaced.
        ``uploadLimit``              5 -                   Set the speed limit for upload in Kib/s.
        ``uploadLimited``            5 -                   Enable upload speed limiter.
        ============================ ===== =============== =======================================================================================

    	.. NOTE::
    	   transmissionrpc will try to automatically fix argument errors.
        """
        args = {}
        for key, value in iteritems(kwargs):
            argument = make_rpc_name(key)
            (arg, val) = argument_value_convert('torrent-set' , argument, value, self.rpc_version)
            args[arg] = val

        if len(args) > 0:
            self._request('torrent-set', args, ids, True, timeout=timeout)
        else:
            ValueError("No arguments to set")

    def change(self, ids, timeout=None, **kwargs):
        """

        .. WARNING::
            Deprecated, please use change_torrent.
        """
        warnings.warn('change has been deprecated, please use change_torrent instead.', DeprecationWarning)
        self.change_torrent(ids, timeout, **kwargs)

    def move_torrent_data(self, ids, location, timeout=None):
        """Move torrent data to the new location."""
        self._rpc_version_warning(6)
        args = {'location': location, 'move': True}
        self._request('torrent-set-location', args, ids, True, timeout=timeout)

    def move(self, ids, location, timeout=None):
        """

        .. WARNING::
            Deprecated, please use move_torrent_data.
        """
        warnings.warn('move has been deprecated, please use move_torrent_data instead.', DeprecationWarning)
        self.move_torrent_data(ids, location, timeout)

    def locate_torrent_data(self, ids, location, timeout=None):
        """Locate torrent data at the provided location."""
        self._rpc_version_warning(6)
        args = {'location': location, 'move': False}
        self._request('torrent-set-location', args, ids, True, timeout=timeout)

    def locate(self, ids, location, timeout=None):
        """

        .. WARNING::
            Deprecated, please use locate_torrent_data.
        """
        warnings.warn('locate has been deprecated, please use locate_torrent_data instead.', DeprecationWarning)
        self.locate_torrent_data(ids, location, timeout)

    def rename_torrent_path(self, torrent_id, location, name, timeout=None):
        """
        Rename directory and/or files for torrent.
        Remember to use get_torrent or get_torrents to update your file information.
        """
        self._rpc_version_warning(15)
        torrent_id = parse_torrent_id(torrent_id)
        if torrent_id is None:
            raise ValueError("Invalid id")
        dirname = os.path.dirname(name)
        if len(dirname) > 0:
            raise ValueError("Target name cannot contain a path delimiter")
        args = {'path': location, 'name': name}
        result = self._request('torrent-rename-path', args, torrent_id, True, timeout=timeout)
        return (result['path'], result['name'])

    def queue_top(self, ids, timeout=None):
        """Move transfer to the top of the queue."""
        self._rpc_version_warning(14)
        self._request('queue-move-top', ids=ids, require_ids=True, timeout=timeout)

    def queue_bottom(self, ids, timeout=None):
        """Move transfer to the bottom of the queue."""
        self._rpc_version_warning(14)
        self._request('queue-move-bottom', ids=ids, require_ids=True, timeout=timeout)
        
    def queue_up(self, ids, timeout=None):
        """Move transfer up in the queue."""
        self._rpc_version_warning(14)
        self._request('queue-move-up', ids=ids, require_ids=True, timeout=timeout)

    def queue_down(self, ids, timeout=None):
        """Move transfer down in the queue."""
        self._rpc_version_warning(14)
        self._request('queue-move-down', ids=ids, require_ids=True, timeout=timeout)

    def get_session(self, timeout=None):
        """
        Get session parameters. See the Session class for more information.
        """
        self._request('session-get', timeout=timeout)
        self._update_server_version()
        return self.session

    def set_session(self, timeout=None, **kwargs):
        """
        Set session parameters. The parameters are:

        ================================ ===== ================= ==========================================================================================================================
        Argument                         RPC   Replaced by       Description
        ================================ ===== ================= ==========================================================================================================================
        ``alt_speed_down``               5 -                     Alternate session download speed limit (in Kib/s).
        ``alt_speed_enabled``            5 -                     Enables alternate global download speed limiter.
        ``alt_speed_time_begin``         5 -                     Time when alternate speeds should be enabled. Minutes after midnight.
        ``alt_speed_time_day``           5 -                     Enables alternate speeds scheduling these days.
        ``alt_speed_time_enabled``       5 -                     Enables alternate speeds scheduling.
        ``alt_speed_time_end``           5 -                     Time when alternate speeds should be disabled. Minutes after midnight.
        ``alt_speed_up``                 5 -                     Alternate session upload speed limit (in Kib/s).
        ``blocklist_enabled``            5 -                     Enables the block list
        ``blocklist_url``                11 -                    Location of the block list. Updated with blocklist-update.
        ``cache_size_mb``                10 -                    The maximum size of the disk cache in MB
        ``dht_enabled``                  6 -                     Enables DHT.
        ``download_dir``                 1 -                     Set the session download directory.
        ``download_queue_enabled``       14 -                    Enables download queue.
        ``download_queue_size``          14 -                    Number of slots in the download queue.
        ``encryption``                   1 -                     Set the session encryption mode, one of ``required``, ``preferred`` or ``tolerated``.
        ``idle_seeding_limit``           10 -                    The default seed inactivity limit in minutes.
        ``idle_seeding_limit_enabled``   10 -                    Enables the default seed inactivity limit
        ``incomplete_dir``               7 -                     The path to the directory of incomplete transfer data.
        ``incomplete_dir_enabled``       7 -                     Enables the incomplete transfer data directory. Otherwise data for incomplete transfers are stored in the download target.
        ``lpd_enabled``                  9 -                     Enables local peer discovery for public torrents.
        ``peer_limit``                   1 - 5 peer-limit-global Maximum number of peers.
        ``peer_limit_global``            5 -                     Maximum number of peers.
        ``peer_limit_per_torrent``       5 -                     Maximum number of peers per transfer.
        ``peer_port``                    5 -                     Peer port.
        ``peer_port_random_on_start``    5 -                     Enables randomized peer port on start of Transmission.
        ``pex_allowed``                  1 - 5 pex-enabled       Allowing PEX in public torrents.
        ``pex_enabled``                  5 -                     Allowing PEX in public torrents.
        ``port``                         1 - 5 peer-port         Peer port.
        ``port_forwarding_enabled``      1 -                     Enables port forwarding.
        ``queue_stalled_enabled``        14 -                    Enable tracking of stalled transfers.
        ``queue_stalled_minutes``        14 -                    Number of minutes of idle that marks a transfer as stalled.
        ``rename_partial_files``         8 -                     Appends ".part" to incomplete files
        ``script_torrent_done_enabled``  9 -                     Whether or not to call the "done" script.
        ``script_torrent_done_filename`` 9 -                     Filename of the script to run when the transfer is done.
        ``seed_queue_enabled``           14 -                    Enables upload queue.
        ``seed_queue_size``              14 -                    Number of slots in the upload queue.
        ``seedRatioLimit``               5 -                     Seed ratio limit. 1.0 means 1:1 download and upload ratio.
        ``seedRatioLimited``             5 -                     Enables seed ration limit.
        ``speed_limit_down``             1 -                     Download speed limit (in Kib/s).
        ``speed_limit_down_enabled``     1 -                     Enables download speed limiting.
        ``speed_limit_up``               1 -                     Upload speed limit (in Kib/s).
        ``speed_limit_up_enabled``       1 -                     Enables upload speed limiting.
        ``start_added_torrents``         9 -                     Added torrents will be started right away.
        ``trash_original_torrent_files`` 9 -                     The .torrent file of added torrents will be deleted.
        ``utp_enabled``                  13 -                    Enables Micro Transport Protocol (UTP).
        ================================ ===== ================= ==========================================================================================================================

        .. NOTE::
    	   transmissionrpc will try to automatically fix argument errors.
        """
        args = {}
        for key, value in iteritems(kwargs):
            if key == 'encryption' and value not in ['required', 'preferred', 'tolerated']:
                raise ValueError('Invalid encryption value')
            argument = make_rpc_name(key)
            (arg, val) = argument_value_convert('session-set' , argument, value, self.rpc_version)
            args[arg] = val
        if len(args) > 0:
            self._request('session-set', args, timeout=timeout)

    def blocklist_update(self, timeout=None):
        """Update block list. Returns the size of the block list."""
        self._rpc_version_warning(5)
        result = self._request('blocklist-update', timeout=timeout)
        if 'blocklist-size' in result:
            return result['blocklist-size']
        return None

    def port_test(self, timeout=None):
        """
        Tests to see if your incoming peer port is accessible from the
        outside world.
        """
        self._rpc_version_warning(5)
        result = self._request('port-test', timeout=timeout)
        if 'port-is-open' in result:
            return result['port-is-open']
        return None

    def free_space(self, path, timeout=None):
        """
        Get the ammount of free space (in bytes) at the provided location.
        """
        self._rpc_version_warning(15)
        result = self._request('free-space', {'path': path}, timeout=timeout)
        if result['path'] == path:
            return result['size-bytes']
        return None

    def session_stats(self, timeout=None):
        """Get session statistics"""
        self._request('session-stats', timeout=timeout)
        return self.session
