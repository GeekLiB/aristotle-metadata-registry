"Misc. utility functions/classes for admin documentation generator."
# Once the contrib.help functionality is completed this module will become deprecated.

import re
from email.errors import HeaderParseError
from email.parser import HeaderParser

from django.core.urlresolvers import reverse
from django.utils.encoding import force_bytes
from django.utils.safestring import mark_safe

try:
    import docutils.core
    import docutils.nodes
    import docutils.parsers.rst.roles
except ImportError:
    docutils_is_available = False
else:
    docutils_is_available = True

from django.contrib.admindocs.utils import (
    trim_docstring, parse_docstring
)


def parse_rst(text, default_reference_context, thing_being_parsed=None):
    """
    Convert the string from reST to an XHTML fragment.
    """
    overrides = {
        'doctitle_xform': True,
        'inital_header_level': 3,
        "default_reference_context": default_reference_context,
        "link_base": reverse('django-admindocs-docroot').rstrip('/'),
        'raw_enabled': False,
        'file_insertion_enabled': False,
    }
    if thing_being_parsed:
        thing_being_parsed = force_bytes("<%s>" % thing_being_parsed)
    # Wrap ``text`` in some reST that sets the default role to ``cmsreference``,
    # then restores it.
    source = """
.. default-role:: cmsreference

%s

.. default-role::
"""
    parts = docutils.core.publish_parts(
        source % text,
        source_path=thing_being_parsed, destination_path=None,
        writer_name='html', settings_overrides=overrides
    )
    return mark_safe(parts['fragment'])
