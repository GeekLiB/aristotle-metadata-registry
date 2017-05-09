from django.conf.urls import url
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from django.utils.translation import ugettext_lazy as _

from aristotle_mdr.contrib.generic.views import (
    GenericAlterOneToManyView,
    generic_foreign_key_factory_view
)

from aristotle_mdr.contrib.links import models, views


urlpatterns = [
    url(r'^relation/(?P<iid>\d+)?/relation/edit/roles/?$',
        GenericAlterOneToManyView.as_view(
            model_base=models.Relation,
            model_to_add=models.RelationRole,
            model_base_field='relationrole_set',
            model_to_add_field='relation',
            ordering_field='ordinal',
            form_add_another_text=_('Add a role'),
            form_title=_('Change Relation Roles'),
        ), name='relation_roles_edit'),
    url(r'^relation/link/add/$',
        views.AddLinkWizard.as_view(), name='add_link'),
    url(r'^relation/link/edit/(?P<iid>\d+)$',
        views.EditLinkFormView.as_view(), name='edit_link'),
    url(r'^relation/link/json/(?P<iid>\d+)$',
        views.link_json_for_item, name='link_json_for_item'),
]
