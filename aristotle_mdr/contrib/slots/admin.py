from django.contrib import admin
from reversion_compare.admin import CompareVersionAdmin
from aristotle_mdr.contrib.slots import models
import reversion


class SlotInline(admin.TabularInline):
    model = models.Slot


reversion.revisions.register(models.Slot)
