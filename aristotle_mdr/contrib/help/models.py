"""
Aristotle Help models
=====================
"""

from django.apps import apps
from django.db import models
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.conf.global_settings import LANGUAGES
from aristotle_mdr.models import RichTextField
from model_utils.models import TimeStampedModel
from autoslug import AutoSlugField


class HelpBase(TimeStampedModel):
    """
    The base help class for Aristotle help pages.
    """
    slug = AutoSlugField(populate_from='title')
    app_label = models.CharField(
        max_length=256, null=True, blank=True,
        help_text=_('Add an app for app specific help, required for concept help')
        )
    title = models.TextField(
        help_text=_("A short title for the help page")
    )
    body = RichTextField(
        null=True, blank=True,
        help_text=_("A long help definition for an object or topic")
    )
    language = models.CharField(
        max_length=7, choices=LANGUAGES
    )
    is_public = models.BooleanField(
        default=True,
        help_text=_("Indicates if a help topic is available to non-registered users."),
    )
    unique_together = ("app_label", "title", "language")


class HelpPage(HelpBase):
    """
    A help page is a generic way of providing help to a user on a topic.
    """
    class Meta:
        ordering = ('title',)


class ConceptHelp(HelpBase):
    """
    A Concept help page documents a given model that inherits from an
    11179 concept.
    """
    class Meta:
        ordering = ('concept_type', 'app_label')

    concept_type = models.CharField(max_length=256)
    brief = models.TextField(
        help_text=_("A short description of the concept")
    )
    offical_definition = models.TextField(
        null=True, blank=True,
        help_text=_("An official description of the concept, e.g. the ISO/IEC definition for an Object Class")
    )
    official_reference = models.TextField(
        null=True, blank=True,
        help_text=_("The reference document that describes this concept type")
    )
    official_link = models.TextField(
        null=True, blank=True,
        help_text=_("An link to an official source for a description of the concept")
    )
    creation_tip = RichTextField(
        null=True, blank=True,
        help_text=_("Instructions for creating good content of this type")
    )
    unique_together = ("app_label", "concept_type", "language")

    def natural_key(self):
        return (self.app_label, self.concept_type, self.language)

    def get_app(self):
        return apps.get_app_config(self.app_label)

    def get_model(self):
        from django.contrib.contenttypes.models import ContentType
        return ContentType.objects.get(
            app_label=self.app_label,
            model=self.concept_type
            ).model_class()

    def validate_unique(self, exclude=None):
        qs = ConceptHelp.objects.exclude(pk=self.pk).filter(
            app_label=self.app_label,
            concept_type=self.concept_type,
            language=self.language)
        if qs.exists():
            raise ValidationError('App / Concept / Language must be unique per site')

    def save(self):
        self.validate_unique()
        if not self.app_label:
            raise ValidationError('ConceptHelp must have an app')
        self.title = _("Help for concept type %s") % self.get_model()._meta.verbose_name
        super(ConceptHelp, self).save()
