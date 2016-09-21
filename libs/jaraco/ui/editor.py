from __future__ import unicode_literals, absolute_import

import tempfile
import os
import sys
import subprocess
import mimetypes
import collections
import io
import difflib

import six

class EditProcessException(RuntimeError): pass

class EditableFile(object):
	"""
	EditableFile saves some data to a temporary file, launches a
	platform editor for interactive editing, and then reloads the data,
	setting .changed to True if the data was edited.

	e.g.::

		x = EditableFile('foo')
		x.edit()

		if x.changed:
			print(x.data)

	The EDITOR environment variable can define which executable to use
	(also XML_EDITOR if the content-type to edit includes 'xml'). If no
	EDITOR is defined, defaults to 'notepad' on Windows and 'edit' on
	other platforms.
	"""
	platform_default_editors = collections.defaultdict(
		lambda: 'edit',
		win32 = 'notepad',
		linux2 = 'vi',
	)
	encoding = 'utf-8'

	def __init__(self, data='', content_type='text/plain'):
		self.data = six.text_type(data)
		self.content_type = content_type

	def __enter__(self):
		extension = mimetypes.guess_extension(self.content_type) or ''
		fobj, self.name = tempfile.mkstemp(extension)
		os.write(fobj, self.data.encode(self.encoding))
		os.close(fobj)
		return self

	def read(self):
		with open(self.name, 'rb') as f:
			return f.read().decode(self.encoding)

	def __exit__(self, *tb_info):
		os.remove(self.name)

	def edit(self):
		"""
		Edit the file
		"""
		self.changed = False
		with self:
			editor = self.get_editor()
			cmd = [editor, self.name]
			try:
				res = subprocess.call(cmd)
			except Exception as e:
				print("Error launching editor %(editor)s" % locals())
				print(e)
				return
			if res != 0:
				msg = '%(editor)s returned error status %(res)d' % locals()
				raise EditProcessException(msg)
			new_data = self.read()
			if new_data != self.data:
				self.changed = self._save_diff(self.data, new_data)
				self.data = new_data

	@staticmethod
	def _search_env(keys):
		"""
		Search the environment for the supplied keys, returning the first
		one found or None if none was found.
		"""
		matches = (os.environ[key] for key in keys if key in os.environ)
		return next(matches, None)

	def get_editor(self):
		"""
		Give preference to an XML_EDITOR or EDITOR defined in the
		environment. Otherwise use a default editor based on platform.
		"""
		env_search = ['EDITOR']
		if 'xml' in self.content_type:
			env_search.insert(0, 'XML_EDITOR')
		default_editor = self.platform_default_editors[sys.platform]
		return self._search_env(env_search) or default_editor

	@staticmethod
	def _save_diff(*versions):
		def get_lines(content):
			return list(io.StringIO(content))
		lines = map(get_lines, versions)
		diff = difflib.context_diff(*lines)
		return tuple(diff)
