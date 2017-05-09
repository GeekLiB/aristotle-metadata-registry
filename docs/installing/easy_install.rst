Easy installer documentation
----------------------------

This is a quick guide to setting up a new metadata registry based on
the Aristotle Metadata Registry framework using the easy installer.

Such a server should be considered for *demonstration* purposes, and deployment
should be done in accordance with the best practices and specific requirements
of the installing agency.

For more information on configuring a more complete installation review the help article
:doc:`/installing/integrate_with_django_project`.

1. Make sure you have a server setup for hosting the project with an appropriate
   WSGI web server configured. If the server is only used for development, the inbuilt
   django server can be accessed by running the ``./manage.py runserver`` command.

   `PythonAnywhere also provides a free python server suitable for development and low
   traffic sites <http://www.PythonAnywhere.com>`_.

2. (Optional but recommended) Configure a ``virtualenv`` for your server, so that the dependancies
   for Aristotle-MDR do conflict any other software you may be running. If you are running
   Aristotle on an isolated server with root privileges you may skip this step.

   For PythonAnywhere, information is available on
   `installing virtualenv <https://www.pythonanywhere.com/wiki/InstallingVirtualenvWrapper>`_
   and `configuring a new virtualenv <https://www.pythonanywhere.com/wiki/VirtualEnvForNewerDjango>`_.

3. Fetch the example metadata registry stored within the
   `Aristotle-MDR GitHub repository <https://github.com/aristotle-mdr/aristotle-metadata-registry>`_.

   On a linux machine, this can be done with the command::

      pip install aristotle-metadata-registry
      python -m aristotle_mdr.install.easy

4. Run the easy installer: ``aristotle_mdr.install.easy``. There are a number of command line arguments
   that are explained in the help documentation which can be accessed from the command line::

    python -m aristotle_mdr.install.easy --help

   This will setup an example registry, and will prompt you for a new name, ask for a few
   additional settings, install requirements, setup a database and set up the static files.

5. If required, browse to the directory of your project that was named in the above directory,
   and edit the ``settings.py`` files to meet your requirements.
   Although the installer generates a pseudo-random hash for the ``SECRET_KEY``, 
   **It is strongly recommmended you generate a fresh** ``SECRET_KEY``. Also consider which
   customisations to implement using the options in the ``ARISTOTLE_SETTINGS``
   dictionary - details of which can be found under :doc:`/installing/settings`.
   
   The example registry includes commented out lines for some useful Aristotle-MDR extensions.
   If you wish to use these, remove the comments as directed by the documentation in ``settings.py``.

6. If you are using a WSGI server (such as PythonAnywhere) you'll need to either point your server to
   the projects ``wsgi.py`` file or update your WSGI configuration.

   For more information on `configuring the PythonAnywhere WSGI server review their documentation <https://www.pythonanywhere.com/wiki/DjangoTutorial>`_.

7. Start (or restart) the development server and visit its address.
   In the case of a local development server this will likely be ``127.0.0.1``.

Using a different database
==========================

The easy installer using a simple SQLite database for storing content, however for
large scale production servers with multiple concurrent users this may not be
appropriate. `Django supports a wide range of database server <https://docs.djangoproject.com/en/stable/ref/databases/>`_
which can be used instead of SQLite. However to the very specific nature of the
options required to connect to a database, to use an alternate database with
the easy installer a few additional steps are required.

1. Let the installer run to completion, without the ``--dry`` option, and
   selecting yes when asked ``Ready to install requirements? (y/n):``.

2. Edit your ``settings.py`` file and add a variable ``DATABASES`` set to connect
   to your `database as described in the Django documentation <https://docs.djangoproject.com/en/stable/ref/databases/>`_.

3. Remove the ``pos.db3`` file that will have been created during the installation.
   This file is the name of the default SQLite database and can be safely deleted
   without any issues.

4. Call the Django ``migrate`` command again using the updated settings::

    ./manage.py migrate

5. Start (or restart) the development server and visit its address.
   In the case of a local development server this will likely be ``127.0.0.1``.

Disabling the DEBUG options
===========================

Because of the The easy installer using a simple SQLite database for storing content, however for
large scale production servers with multiple concurrent users this may not be
appropriate. `Django supports a wide range of database servers <https://docs.djangoproject.com/en/stable/ref/databases/>`_
which can be used instead of SQLite. However to the very specific nature of the
options required to connect to a a database, to use an alternate database with
the easy installer a few additional steps are required.

1. Let the installer run to completion, without the ``--dry`` option, and
   selecting yes when asked ``Ready to install requirements? (y/n):``.

2. Edit your ``settings.py`` file and set the ``DEBUG`` to False::
    DEBUG=False

3. Remove the ``pos.db3`` file that will have been created during the installation.
   This file is the name of the default SQLite database and will have a number of
   example objects and users created within it as the migrate step when ``DEBUG``
   is set to ``True``.

4. Call the Django ``migrate`` command again using the updated settings::

    ./manage.py migrate

5. Start (or restart) the development server and visit its address.
   In the case of a local development server this will likely be ``127.0.0.1``.
   To access the administators sections of the site you will need to create
   a super user.

Creating a superuser for the registry
=====================================

`Creating a superuser is covered in more depth in the Django documentation <https://docs.djangoproject.com/en/1.8/ref/django-admin/#django-admin-createsuperuser>`_,
however a quick guide is given here. These steps assume a valid database exists
and has been appropriately set up with the Django ``migrate`` command.

To create a super user, browse to the project folder and run the command::

    $ django-admin createsuperuser

This will prompt you for a username, email and password.

A username and email can be applied with the ``--username`` and ``--email``
switches respectively. For example::

    $ django-admin createsuperuser  --username=my_registry_admin --email=admin@registry.example.gov
