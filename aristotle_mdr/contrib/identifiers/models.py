"""
Aristotle MDR 11179 Identification models
=========================================

These are based on the Identification metadamodel region in ISO/IEC 11179 Part 3 - 7.2.1
"""

from django.db import models
from django.utils.encoding import python_2_unicode_compatible  # Python 2
from django.utils.translation import ugettext_lazy as _

from model_utils.models import TimeStampedModel
from aristotle_mdr import models as MDR


class Namespace(TimeStampedModel):
    naming_authority = models.ForeignKey(MDR.Organization)  # 7.2.2.3.2.1
    shorthand_prefix = models.CharField(  # 7.2.2.3.2.5
        max_length=512,
        help_text=_('prefix conventionally used as shorthand for a namespace, for greater readability, in text for human consumption.')
    )

    def __str__(self):
        return u"{0}:{1}".format(self.naming_authority.name, self.shorthand_prefix)


@python_2_unicode_compatible  # Python 2
class ScopedIdentifier(TimeStampedModel):
    namespace = models.ForeignKey(Namespace)
    concept = models.ForeignKey(MDR._concept, related_name='identifiers')
    identifier = models.CharField(  # 7.2.2.2.2.1
        max_length=512,
        help_text=_('String used to unambiguously denote an Item within the scope of a specified Namespace.')
    )
    version = models.CharField(  # 7.2.2.2.2.2
        max_length=512,
        help_text=_('unique version identifier of the Scoped_Identifier which identifies an Item'),
        blank=True,
        default=""
    )

    class Meta:
        unique_together = ("namespace", "identifier", "version")

    def __str__(self):
        return u"{0}:{1}:{2}".format(self.namespace.naming_authority.name, self.identifier, self.version)

    @property
    def prefix(self):
        return self.namespace.shorthand_prefix
