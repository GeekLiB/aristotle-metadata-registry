from django.db.models import Q
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib.admin.filters import RelatedFieldListFilter
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _


from aristotle_mdr.search_indexes import conceptIndex
from aristotle_mdr.contrib.links import models as links
from aristotle_mdr.contrib.links import forms as forms

from aristotle_mdr.register import register_concept


class RoleRelationInline(admin.TabularInline):
    model = links.RelationRole
    fields = ("ordinal", "name", "definition", "multiplicity",)
    extra = 1


register_concept(
    links.Relation,
    extra_fieldsets=[('Extra details', {'fields': ['arity']})],
    extra_inlines=[RoleRelationInline],
    reversion={
        'follow': ['relationrole_set'],
        'follow_classes': [links.RelationRole]
    }
)
