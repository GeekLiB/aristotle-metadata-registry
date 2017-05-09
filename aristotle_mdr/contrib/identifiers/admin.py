from django.contrib import admin
from reversion_compare.admin import CompareVersionAdmin
from aristotle_mdr.contrib.identifiers import models
import reversion


class NamespaceAdmin(admin.ModelAdmin):
    list_display = ('naming_authority', 'shorthand_prefix')
    list_filter = ('naming_authority', 'shorthand_prefix')
    search_fields = ('naming_authority', 'shorthand_prefix')


admin.site.register(models.Namespace, NamespaceAdmin)


class ScopedIdentifierInline(admin.TabularInline):
    model = models.ScopedIdentifier


reversion.revisions.register(models.ScopedIdentifier)
