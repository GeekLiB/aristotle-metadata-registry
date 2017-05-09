Integrating Aristotle-MDR with a Django project
-----------------------------------------------

**Note:** this guide relies on some experience with Python and Django.
For new users looking at getting a site up and running look at the
:doc:`/installing/easy_install`.

The first step is `starting a project as described in the Django tutorial <https://docs.djangoproject.com/en/1.7/intro/tutorial01/>`_.
Once this is done, follow the steps below to setup Aristotle-MDR.

1. Add "aristotle_mdr" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = (
        ...
        'haystack',
        'aristotle_mdr',
        ...
    )

   To ensure that search indexing works properly `haystack` **must** be installed before `aristotle_mdr`.
   If you want to take advantage of Aristotle's WCAG-2.0 access-key shortcut improvements for the admin interface,
   make sure it is installed *before* the django admin app.

2. Include the Aristotle-MDR URLconf in your project urls.py. Because Aristotle will
   form the majority of the interactions with the site, as well as including a
   number of URLconfs for supporting apps its recommended to included it at the
   server root, like this::

    url(r'^/', include('aristotle_mdr.urls')),

3. Create the database for the metadata registry using the Django migrate command::

    python manage.py migrate

4. Start the development server with ``python manage.py runserver`` and visit http://127.0.0.1:8000/
   to see the home page.

For a complete example of how to successfully include Aristotle, see the `example_mdr` directory.
