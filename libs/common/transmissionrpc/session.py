# -*- coding: utf-8 -*-
# Copyright (c) 2008-2013 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

from transmissionrpc.utils import Field

from six import iteritems, integer_types

class Session(object):
    """
    Session is a class holding the session data for a Transmission daemon.

    Access the session field can be done through attributes.
    The attributes available are the same as the session arguments in the
    Transmission RPC specification, but with underscore instead of hyphen.
    ``download-dir`` -> ``download_dir``.
    """

    def __init__(self, client=None, fields=None):
        self._client = client
        self._fields = {}
        if fields is not None:
            self._update_fields(fields)

    def __getattr__(self, name):
        try:
            return self._fields[name].value
        except KeyError:
            raise AttributeError('No attribute %s' % name)

    def __str__(self):
        text = ''
        for key in sorted(self._fields.keys()):
            text += "% 32s: %s\n" % (key[-32:], self._fields[key].value)
        return text

    def _update_fields(self, other):
        """
        Update the session data from a Transmission JSON-RPC arguments dictionary
        """
        if isinstance(other, dict):
            for key, value in iteritems(other):
                self._fields[key.replace('-', '_')] = Field(value, False)
        elif isinstance(other, Session):
            for key in list(other._fields.keys()):
                self._fields[key] = Field(other._fields[key].value, False)
        else:
            raise ValueError('Cannot update with supplied data')

    def _dirty_fields(self):
        """Enumerate changed fields"""
        outgoing_keys = ['peer_port', 'pex_enabled']
        fields = []
        for key in outgoing_keys:
            if key in self._fields and self._fields[key].dirty:
                fields.append(key)
        return fields

    def _push(self):
        """Push changed fields to the server"""
        dirty = self._dirty_fields()
        args = {}
        for key in dirty:
            args[key] = self._fields[key].value
            self._fields[key] = self._fields[key]._replace(dirty=False)
        if len(args) > 0:
            self._client.set_session(**args)

    def update(self, timeout=None):
        """Update the session information."""
        self._push()
        session = self._client.get_session(timeout=timeout)
        self._update_fields(session)
        session = self._client.session_stats(timeout=timeout)
        self._update_fields(session)

    def from_request(self, data):
        """Update the session information."""
        self._update_fields(data)

    def _get_peer_port(self):
        """
        Get the peer port.
        """
        return self._fields['peer_port'].value

    def _set_peer_port(self, port):
        """
        Set the peer port.
        """
        if isinstance(port, integer_types):
            self._fields['peer_port'] = Field(port, True)
            self._push()
        else:
            raise ValueError("Not a valid limit")

    peer_port = property(_get_peer_port, _set_peer_port, None, "Peer port. This is a mutator.")

    def _get_pex_enabled(self):
        """Is peer exchange enabled?"""
        return self._fields['pex_enabled'].value

    def _set_pex_enabled(self, enabled):
        """Enable/disable peer exchange."""
        if isinstance(enabled, bool):
            self._fields['pex_enabled'] = Field(enabled, True)
            self._push()
        else:
            raise TypeError("Not a valid type")

    pex_enabled = property(_get_pex_enabled, _set_pex_enabled, None, "Enable peer exchange. This is a mutator.")
