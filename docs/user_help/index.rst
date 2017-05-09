Creating and deploying user help
================================

.. toctree::
   :maxdepth: 2

   help_types.rst
   help_syntax.rst

Writing help files
------------------

To improve users abilities to self-help and self-manage within an instance the
Aristotle Metadata Registry includes a help API that allows system administrators,
and extension and download developers to write help files that are searchable by
users.

At their core, these help files are similar to django fixture files with
a few relatively minor differences.

* The subclassing of help files needed for indexing can be ignored
* One fixture per file is recommended to make writing easier, although multiple help pages can be parsed from one file

Importing help files
--------------------

The Aristotle-MDR provides a django command line action similar to the ``loadata``
called ``load_aristotle_help``. This adds an additional switch ``--update`` or ``-U`` that 
when attempting to insert, will instead override help files.

For example::

   ./manage.py load_aristotle_help

Will load all help files in the ``./aristotle_help_files/`` subdirectory of *all apps in ``INSTALLED_APPS``*.

Accessing help in extension and download templates
--------------------------------------------------

Aristotle provides a template tag to extract a number of different help types for
11179-derived concepts in templates.

This can be called using ``help_doc`` and passing the model class for the concept
required along with the help field requested.
   
   {% load aristotle_help %}
   {% help_doc model_class 'brief' %}
