Adding new bulk actions
=======================

Often for user convenience it is useful to perfom the same action across a
number of similar metadata items. Aristotle-MDR provides a bulk action API that
allows developers to create new discoverable action types that are shown to
users in certain item lists, such as search results or workgroup item listings.

Registering a bulk action
-------------------------

The ``BULK_ACTIONS`` :doc:`setting <../extensions/bulk_actions>` in the 
in the ``ARISTOTLE_SETTINGS`` dictionary stores the register of bulk actions
used for generating lists. Adding a name for the action and the qualified path
to the form is sufficient to register a new bulk action.
For example this set in ``ARISTOTLE_SETTINGS`` would register an action called
``my_action`` with the Python location ``module.forms.MyBulkAction``::

    'BULK_ACTIONS': {
        'my_action':'module.forms.MyBulkActionForm',
        }

Writing a functional bulk action
--------------------------------

A bulk action form is just a specialised Django form for acting on multiple 
Aristotle-MDR concepts, with a few small additions that come from inheriting
from ``aristotle_mdr.forms.bulk_actions.BulkActionForm``.

After inheriting to make a form function some properties should exist.

* ``action_text`` - This is the name for an action shown in lists to users.
  *Default* is based on the class name.
* ``classes`` - A string of HTML classes that will be applied to each item.
  *Default* empty.
  Currently these are used for inserting 'Font Awesome' icons for each action.
* ``confirm_page`` - An optional template name used to render between a user 
  clicking the action and completing it. By adding extra fields to a form, with
  this template a bulk action can get additional inforamtion from a user before
  continuing. *No default*, if this is empty no confirmation is requested.
* ``items_label`` - An optional override of the label for the list of items the 
  action form acts on. Defaults to "Select some items"
  
There are two additional methods that complete the class:

* ``can_use`` - A ``classmethod`` that provides a boolean response indicating if
  a certain user has permission to use this action in any context - note this
  permission does not have knowledge of the items selected. *Default* is true, 
  so if this is not overriden all users will see the action in their list.
* ``make_changes`` - Performs that actual action of the form, this is called 
  once the user invokes a bulk action (after confirmation is required).
  *No default*, not including a ``make_changes`` method will cause your action to
  fail. Any text returned from this method will be shown to a user via the
  django messages framework.

An example bulk action form
---------------------------
Below is an example bulk action that is only visible for staff users, and
deletes the items requested by a user.:
    
.. literalinclude:: /../aristotle_mdr/tests/apps/bulk_actions_test/actions.py
    :caption: mymodule.forms.StaffDeleteActionForm
    :end-before: # Incomplete test bulk actions

.. literalinclude:: /../aristotle_mdr/tests/apps/bulk_actions_test/templates/confirm_delete.html
    :caption: confirm_delete.html
    :language: html

This will produce a button wherever other bulk actions are available, similar to
the 'Delete' button available on the right in the image below.

 .. image:: /_static/bulk_action_options.png
    :alt: A list of items with bulk actions available.
    :width: 60%
