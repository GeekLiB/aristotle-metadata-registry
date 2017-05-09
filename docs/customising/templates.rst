Customising templates
=====================

Aristotle-MDR builds pages using Django tempaltes.

Which means almost every part of the website can be customised using the
`django template overriding order <https://docs.djangoproject.com/en/1.8/ref/templates/api/#loading-templates>`_.

But default, when building pages Aristotle will try to load templates from the ``site`` directory
first before using templates from Aristolte and extensions or other Django apps.
