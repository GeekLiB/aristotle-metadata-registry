Special syntax in user help files
=================================

As help files are just `django fixture files <https://docs.djangoproject.com/en/1.8/howto/initial-data/>`_
 all of the caveats there apply, with a few small conventions applied on top.

* For consistancy and readability, its encouraged to keep one help fixture per file.
* The body of the help file can be HTML, and this will be displayed to the user unchanged. It is up to documenters to ensure that help files are valid HTML that won't break layout. 

A few additional 

Below is an example help file::

   - model: aristotle_mdr_help.helppage
     fields:
       title: Advanced Search
       language: en
       body: >
         <h2>Restricting search with the advanced search options</h2>
         <p>
             The <a href="/search/">search page</a> provides a form that gives
             users control to filter and sort search results.</p>
         <p>
         <img src="{static}/aristotle_mdr/search_filters.png">
             When searching, the "indexed text" refers to everything crawled by the search engine.