Adding new static pages into Aristotle
======================================

While Aristotle provides a strong framework for setting up a metadata registry,
there some static pages which are important for a site, but unlikely to be changed,
such as the home page, CSS and about pages.

These exist in aristotle as template pages, and like all Django tempaltes are easy to
override with more custom, site-specific content. The first step is to ensure the
settings for the site include a Django ``TEMPLATE_DIR`` directive, like that below::

    TEMPLATE_DIRS = [os.path.join(BASE_DIR, 'templates')]

Setting a separate template directory when using Aristotle ensure that templates
can be easily overriden, without requiring a separate django app or editing of
the main Aristole codebase.

When attempting to resolve templates, one of the first locations checked will be the
directory stated in ``TEMPLATE_DIRS``. Examining the code in the
`Aristotle-MDR code <https://github.com/aristotle-mdr/aristotle-metadata-registry/>`_
should give an understanding of how the templates are laid out if changes are necessary.
