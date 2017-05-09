Making new item types
=====================

Most of the overhead for creating new item types in Aristotle-MDR is taken care
of by inheritance within the Python language and the Django web framework.

For example, creating a new item within the registry requires as little code as::

    import aristotle_mdr
    class Question(aristotle_mdr.models.concept):
        questionText = models.TextField()
        responseLength = models.PositiveIntegerField()

This code creates a new "Question" object in the registry that can be progressed
like any standard item in Aristotle-MDR. Once the the appropriate admin pages are
set up, from a usability and publication standpoint this would be indistinguishable
from an Aristotle-MDR item, and would instantly get a number of
:doc:`features that are available to all Aristotle 'concepts' without having to write any additional code </extensions/new_metadata_types/out_of_the_box_features>`

Once synced with the database, this immediately creates a new item type that not only has
a ``name`` and ``description``, but also can immediately be associated with a workgroup, can be
registered and progressed within the registry and has all of the correct permissions
associated with all of these actions.

Likewise, creating relationships to pre-existing items only requires the correct
application of `Django relationships <https://docs.djangoproject.com/en/stable/topics/db/examples/>`_
such as a ``ForeignKey`` or ``ManyToManyField``, like so:

.. literalinclude:: /../aristotle_mdr/tests/apps/extension_test/models.py
    :caption: mymodule.models.Question
    :start-after: # Start of the question model
    :end-before: # End of the question model

This code, extends our Question model from the previous example and adds an optional
link to the ISO 11179 Data Element model managed by Aristotle-MDR and even adds a new property
on to Data Elements, so that ``myDataElement.questions`` would return of all Questions
that are used to collect information for that Data Element. Its also possible to
:doc:`include content from objects across relations on other pages </extensions/including_extra_content>`
without having to alter the templates of other content types. For example, this would allow
pertinant information about questions to appear on data elements, and vice versa.

Customising the edit page for a new type
----------------------------------------

To maintain consistancy edit pages have a similar look and feel across all
concept types, but some customisation is possible. If one or more fields should
be hidden on an edit page, they can be specified in the ``edit_page_excludes``
property of the new concept class.

An example of this is when an item specifies a ManyToManyField that has special
attributes. This can be hidden on the default edit page like so::

    class Questionnaire(aristotle_mdr.models.concept):
        edit_page_excludes = ['questions']
        questions = models.ManyToManyField(
                Question,
                related_name="questionnaires",
                null=True,blank=True)

Including additional items when downloading a custom concept type
-----------------------------------------------------------------

.. automethod:: aristotle_mdr.models.concept.get_download_items

For example:

.. literalinclude:: /../aristotle_mdr/tests/apps/extension_test/models.py
    :caption: mymodule.models.Questionnaire.get_download_items
    :start-after: # Start of get_download_items
    :end-before: # End of get_download_items

Caveats: ``concept`` versus ``_concept``
----------------------------------------

There is a need for some objects to link to any arbitrary concept, for example
the favourites field of `aristotle.models.AristotleProfile`.
Because of this there is a distinction between the Aristotle-MDR model objects
``concept`` and ``_concept``.

Abstract base classes in Django allow for the easy creation of items that share
similar properties, without introducing additional fields into the database. They also
allow for self-referential ForeignKeys that are restricted to the inherited type, rather
than to the base type.

.. autoclass:: aristotle_mdr.models._concept
.. autoclass:: aristotle_mdr.models.concept

The correct way to use both of these models would be as shown below::

    import aristotle_mdr.models import concept, _concept
    class ReallyComplexExampleItem(concept):
        relatedTo = models.ManyToManyField(_concept)

In this example, the model ``ReallyComplexExampleItem`` inherits from ``concept``,
but also includes a many-to-many relationship that links it to any number of
registerable concepts, such as Data Element or Objects Classes, additionally
because of the inheritance, this would allow links to extended models
such as Questions or even self-referential links to other instances of the
``ReallyComplexExampleItem`` model type.

Retrieving the "true item" when you are returned a ``_concept``.
----------------------------------------------------------------

Because ``_concept`` is not a true abstract class, queries on this table or a Django
``QuerySet`` that reference a ``_concept`` won't return the "actual" object but will
return an object of type ``_concept`` instead. There is a ``item`` property on both the
``_concept`` and ``concept`` classes that will return the properly subclassed item
using the ``get_subclass`` method from ``django-model-utils``.

.. autoattribute:: aristotle_mdr.models._concept.item
.. autoattribute:: aristotle_mdr.models.concept.item

On the inherited ``concept`` class this just returns a reference to the original item - ``self``.
So once the true item is retrieved, this property can be called infinitely without a performance hit.

For example, in code or in a template it is always safe to call an item like so::

    question.item
    question.item.item
    question.item.item.item

When in doubt about what object you are dealing with, calling ``item`` will ensure the
expected item, and not the ``_concept`` parent, is used.
In the very worst case a single additional query is made and the right item is used, in
the best case a very cheap Python property is called and the item is returned straight back.


Setting up search, admin pages and autocompletes for new items types
--------------------------------------------------------------------

The easiest way to configure an item for searching and editing within the
django-admin app is using the ``aristotle_mdr.register.register_concept``
method, described in :doc:`/extensions/new_metadata_types/registering_new_content_types`.


Creating admin pages
++++++++++++++++++++

However, if customisation of Admin pages for an extension is required this can
be done through the creation and registration of classes in the ``admin.py``
file of a Django app.

Because of the intricate permissions around content with the Aristotle Registry,
it's recommended that admin pages for new items extend from the
``aristotle.admin.ConceptAdmin`` class. This helps to ensure that there is a
consistent ordering of fields, and information is exposed only to the correct
users.

The most important property of the ``ConceptAdmin`` class is the ``fieldsets`` property
that defines the inclusion and ordering of fields within the admin site. The easiest
way to extend this is to add extra options to the end of the ``fieldsets`` like so::

    from aristotle_mdr import admin as aristotle_admin

    class QuestionAdmin(aristotle_admin.ConceptAdmin):
        fieldsets = aristotle_admin.ConceptAdmin.fieldsets + [
                ('Question Details',
                    {'fields': ['questionText','responseLength']}),
                ('Relations',
                    {'fields': ['collectedDataElement']}),
        ]

**It is important to always import** ``aristotle.admin`` **with an alias as shown above**,
otherwise there are circular dependancies across various apps when importing which
will prevent the app, and thus the whole site, from being used.

Lastly, Aristotle-MDR provides an easy way to give users a suggestion button when entering a name to
ensure consistancy within the registry. This can be added to an Admin page by specifying the fields that
are used to construct the name - however **these must be fields on the current model**.

For example, if the rules of the registry dictated that a Question name should have the form of
its question text along with the name of the collected Data Element, separated by a pipe (``|``),
the ``QuestionAdmin`` class could include the ``name_suggest_fields`` value of::

    name_suggest_fields = ['questionText','collectedDataElement']

Then to ensure the correct separator is used in ``ARISTOTLE_SETTINGS``
(which is described in :doc:`/installing/settings`)
add ``"Question"`` as a key and ``"|"`` as its value, like so::

    ARISTOTLE_SETTINGS = {
        'SEPARATORS': { 'Question':'|',
                        # Other separators not shown
                     },
    # Other settings not shown
    }

For reference, the complete code for the QuestionAdmin class providing extra
fieldsets, autcompeletes and suggested names is::

    from aristotle_mdr import admin as aristotle_admin

    class QuestionAdmin(aristotle_admin.ConceptAdmin):
        fieldsets = aristotle_admin.ConceptAdmin.fieldsets + [
                ('Question Details',
                    {'fields': ['questionText','responseLength']}),
                ('Relations',
                    {'fields': ['collectedDataElement']}),
        ]
        name_suggest_fields = ['questionText','collectedDataElement']

`For more information on configuring an admin site for Django models, consult the
Django documentation <https://docs.djangoproject.com/en/stable/ref/contrib/admin/>`_.

Making new item types searchable
++++++++++++++++++++++++++++++++

The creation and registration of haystack search indexes is done in the
``search_indexes.py`` file of a Django app.

On an Aristotle-MDR powered site, it is possible to restrict search results across a number of
criteria including the registration status of an item, its workgroup or Registration
Authority or the item type.

In ``aristotle.search_indexes`` there is the convenience class ``conceptIndex`` that
make indexing a new item within the search engine quite easy, and allows new item types to be searched using
these criteria with a minimum of code. Inheriting from this class takes care of nearly
all simple cases when searching for new items, like so::

    from haystack import indexes
    from aristotle_mdr.search_indexes import conceptIndex

    class QuestionIndex(conceptIndex, indexes.Indexable):
        def get_model(self):
            return models.Question

**It is important to import the required models from**  ``aristotle.search_indexes``
directly, otherwise there are circular dependancies in Haystack when importing.
This will prevent the app and the whole site from being used.

The only additional work required is to create a search index template in the
``templates`` directory of your app with a path similar to this::

    template/search/indexes/your_app_name/question_text.txt

This ensures that when Haystack is indexing the site, some content is available
so that items can be queried and weighted accordingly. These templates are passed an ``object``
variable that is the particualr object being indexed.

Sample content for an index for our question would look like this::

    {% include "search/indexes/aristotle_mdr/managedobject_text.txt" %}
    {{ object.questionText }}

Here we include the ``managedobject_text.txt`` which adds generic content for all
concepts into the indexed text, as well as including the ``questionText`` in the index.

If we wanted to include the content from the related Data Element to add more information
for the seach engine to work with we could include this as well, using one of the provided index
template in Aristotle, like so::

    {% include "search/indexes/aristotle_mdr/managedobject_text.txt" %}
    {{ object.questionText }}
    {% include "search/indexes/aristotle_mdr/dataelement_text.txt" with object=object.collectedDataElement only %}

`For more information on creating search templates and configuring search options consult the
Haystack documentation <http://django-haystack.readthedocs.org/>`_. For more information on how
the search templates are generated `read about the Django template engine <https://docs.djangoproject.com/en/1.6/topics/templates/>`_.

Caveats around extending existing item types
--------------------------------------------

This tutorial has covered how to create new items when inheriting from the base
``concept`` type. However, Python and Django allow for extension from any object.
So if you wished to extend and improve on 11179 item it would be perfectly possible
to do so by inheriting from the appropriate class, rather than the abstract ``concept``.
For example, if you wished to extend a Data Element to create a internationalised
DataElement that was only applicable in specific countries, this could be done like so::

    class Country(model.Models):
        name = models.TextField
        ... # Other attributes could also be applied.

    class CountrySpecificDataElement(aristotle.models.DataElement):
        countries = models.ManyToManyField(Country)

Aristotle does not prevent you from doing so, however there are a few issues that
can arise when extending from non-abstract classes:

* Due to the way that Django handles subclassing, all objects subclassed from a
  concrete model will also exist in the database as the subclass and an item that
  belongs to the parent superclass.

  So a ``CountrySpecificDataElement`` would also be a ``DataElement``, so a query like this::

     aristotle.models.DataElement.objects.all()

  Would return both ``DataElement`` s and its subclasses, such as ``CountrySpecificDataElement`` s, however
  depending on the domain and objects, this may be desired behaviour.

* Following from the above, restricted searches for only objects of the parent item type will return
  results from the subclassed item. For example, all searches restricted to a ``DataElement``
  would also return results for ``CountrySpecificDataElement``, and they will
  be displayed in the list as ``DataElement`` *not* as ``CountrySpecificDataElement``.

* Items that inherit from non-abstract classes do not inherit the Django object Managers,
  this is one of the reasons for the decision to make ``concept`` an abstract class.
  As such, it is **strongly adviced** that any new item types that inherit from concrete classes
  specify the :doc:`Aristotle-MDR concept manager</extensions/new_metadata_types/using_concept_manager>`, like so::

    class CountrySpecificDataElement(aristotle.models.DataElement):
        countries = models.ManyToManyField(Country)
        objects = aristotle_mdr.models.ConceptManager()

    Failure to include this may lead to broken code or pages that expose private items.


Creating ``unmanagedContent`` types
-----------------------------------

Not all content needs to undergo a standardisation process, and in fact some content
should only be accessible to administrators. In Aristotle this is termed an "unmanagedObject".
Content types that are unmanaged do not belong to workgroups, and can only be edited by
users with the Django "super user" privileges.

It is perfectly safe to extend from the ``unmanagedObject`` types, however because these
are closer to pure Django objects there are much fewer convenience method set up to
handle them. By default, ``unmanagedContent`` is always visible.

Because of their visibility and strict privileges, they are generally suited to relatively
static items that may vary between individual sites and add context to other items. Inheriting
from this class can be done like so::

    class Country(aristotle.models.unmanagedObject):
        # Inherits name and description.
        isoCode = models.CharField(maxLength=3)

For example, in Aristotle-MDR "Measure" is an ``unmanagedObject`` type, that is used
to give extra context to `UnitOfMeasure` objects.


Including documentation in new content types
--------------------------------------------
To make deploying new content easier, and encourage better documentation, Aristotle
reuses help content built into the Django Web framework. When producing dynamic
documentation, Aristotle uses the Python docstring of a ``concept``-inheriting class
and the field level `help_text` to produce documentation.

This can be seen on in the concept editor, administrator pages, item comparator 
and can be accessed in html pages using the ``doc`` template tag in the ``aristotle_tags``
module.


A complete example of an Aristotle Extension
--------------------------------------------
The first content extension for Aristotle that helps clarify a lot
of the issues around inheritance is the
`Comet Indicator Registry <https://github.com/aristotle-mdr/comet-indicator-registry>`_.
This adds 6 new content types along with admin pages, search indexes and templates and extra content for
display on the included Aristotle ``DataElement`` template - which was all achieved with less than 600 lines of code.
