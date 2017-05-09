"""
Aristotle MDR 11179 Link and Relationship models
================================================

These are based on the Link and Relation definitions in ISO/IEC 11179 Part 3 - 9.1.2.4 - 9.1.2.5
"""

from django.db import models
from django.db.models.signals import pre_save
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible  # Python 2

from model_utils.models import TimeStampedModel

from aristotle_mdr import models as MDR
from aristotle_mdr.signals import pre_save_clean


class Relation(MDR.concept):  # 9.1.2.4
    """
    """
    arity = models.PositiveIntegerField(  # 9.1.2.4.3.1
        help_text=_('number of elements in the relation'),
        validators=[MinValueValidator(2)]
    )


@python_2_unicode_compatible  # Python 2
class RelationRole(MDR.aristotleComponent):  # 9.1.2.5
    name = models.TextField(
        help_text=_("The primary name used for human identification purposes.")
    )
    definition = models.TextField(
        _('definition'),
        help_text=_("Representation of a concept by a descriptive statement "
                    "which serves to differentiate it from related concepts. (3.2.39)")
    )
    multiplicity = models.PositiveIntegerField(  # 9.1.2.5.3.1
        # a.k.a the number of times it can appear in a link :(
        help_text=_(
            'number of links which must (logically) be members of the source '
            'relation of this role, differing only by an end with this role as '
            'an end_role.'
        ),
        null=True,
        blank=True,
    )
    ordinal = models.PositiveIntegerField(  # 9.1.2.5.3.2
        help_text=_(
            'order of the relation role among other relation roles in the relation.'
        )
    )
    relation = models.ForeignKey(Relation)

    @property
    def parentItem(self):
        return self.relation

    def __str__(self):
        return "{0.name}".format(self)


class Link(TimeStampedModel):
    """
    Link is a class each instance of which models a link (3.2.69).
    A link is a member of a relation (3.2.119) (not an instance of a relation).
    In relational database parlance, a link would be a tuple (row) in a relation (table).
    Link is a subclass of Assertion (9.1.2.3), and as such is included in one or more
    Concept_Systems (9.1.2.2) through the assertion_inclusion (9.1.3.5) association.
    """
    relation = models.ForeignKey(Relation)

    def concepts(self):
        return MDR._concept.objects.filter(linkend__link=self).all().distinct()

    def add_link_end(self, role, concept):
        return LinkEnd.objects.create(link=self, role=role, concept=concept)


class LinkEnd(TimeStampedModel):  # 9.1.2.7
    link = models.ForeignKey(Link)
    role = models.ForeignKey(RelationRole)
    concept = models.ForeignKey(MDR._concept)

    def clean(self):
        if self.role.relation != self.link.relation:
            raise ValidationError(
                _('A link ends role relation must be from the relation itself')
            )

pre_save.connect(pre_save_clean, sender=LinkEnd)
