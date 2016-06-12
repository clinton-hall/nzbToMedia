# coding=utf-8
# code copied from http://www.doughellmann.com/PyMOTW/urllib2/

from email.generator import _make_boundary as make_boundary
import itertools
import mimetypes


class MultiPartForm(object):
    """Accumulate the data to be used when posting a form."""

    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = make_boundary()
        return

    def get_content_type(self):
        return 'multipart/form-data; boundary={0}'.format(self.boundary)

    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, value))
        return

    def add_file(self, fieldname, filename, fileHandle, mimetype=None):
        """Add a file to be uploaded."""
        body = fileHandle.read()
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.files.append((fieldname, filename, mimetype, body))
        return

    def __str__(self):
        """Return a string representing the form data, including attached files."""
        # Build a list of lists, each containing "lines" of the
        # request.  Each part is separated by a boundary string.
        # Once the list is built, return a string where each
        # line is separated by '\r\n'.  
        parts = []
        part_boundary = '--{boundary}'.format(boundary=self.boundary)

        # Add the form fields
        parts.extend(
            [part_boundary,
             'Content-Disposition: form-data; name="{0}"'.format(name),
             '',
             value,
             ]
            for name, value in self.form_fields
        )

        # Add the files to upload
        parts.extend(
            [part_boundary,
             'Content-Disposition: file; name="{0}"; filename="{1}"'.format(field_name, filename),
             'Content-Type: {0}'.format(content_type),
             '',
             body,
             ]
            for field_name, filename, content_type, body in self.files
        )

        # Flatten the list and add closing boundary marker,
        # then return CR+LF separated data
        flattened = list(itertools.chain(*parts))
        flattened.append('--{boundary}--'.format(boundary=self.boundary))
        flattened.append('')
        return '\r\n'.join(flattened)
