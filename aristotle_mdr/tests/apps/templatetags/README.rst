This test project includes a number of templates that will test the template tags in
``/aristotle_mdr/template_tags/``. In this directory is a ``templates`` directory, which will
have nested directories of the form::

    /templates/{module_name}/{method_name}/{test_name}.html
    
For example:

    /templates/aristotle_tags/extra_content/no_content_for_bad_model.html
    
These templates are ten invoked in ``tests/main/test_templatetags.py`` testrunner.