import datetime
import haystack.indexes as indexes

import aristotle_mdr.models as models
from django.db.models import Q
from django.template import TemplateDoesNotExist
from django.utils import timezone

import logging
logger = logging.getLogger(__name__)
logger.debug("Logging started for " + __name__)

BASE_RESTRICTION = {
    0: 'Public',
    1: 'Locked',
    2: 'Unlocked',
}
RESTRICTION = {}
# reverse the dictionary to make two-way look ups easier
RESTRICTION.update([(k, v) for k, v in BASE_RESTRICTION.items()])
RESTRICTION.update([(str(k), v) for k, v in BASE_RESTRICTION.items()])
RESTRICTION.update([(v, k) for k, v in BASE_RESTRICTION.items()])

registered_indexes = []


class ConceptFallbackCharField(indexes.CharField):
    def prepare_template(self, obj):
        try:
            return super(ConceptFallbackCharField, self).prepare_template(obj)
        except TemplateDoesNotExist:

            logger.debug("No search template found for %s, using untyped fallback." % obj)

            self.template_name = "search/indexes/aristotle_mdr/untyped_concept_text.txt"
            return super(ConceptFallbackCharField, self).prepare_template(obj)


class baseObjectIndex(indexes.SearchIndex):
    text = ConceptFallbackCharField(document=True, use_template=True)
    modified = indexes.DateTimeField(model_attr='modified')
    created = indexes.DateTimeField(model_attr='created')
    name = indexes.CharField(model_attr='name', boost=1)
    # access = indexes.MultiValueField()

    def get_model(self):
        raise NotImplementedError  # pragma: no cover -- This should always be overridden

    # From http://unfoldthat.com/2011/05/05/search-with-row-level-permissions.html
    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""

        return self.get_model().objects.filter(modified__lte=timezone.now())

    # def have_access(self, obj):
    #    for user in obj.viewers.users():
    #        yield user

    #    for group in obj.viewers.groups():
    #        yield group

    # def prepare_access(self, obj):
    #    def _access_iter(obj):
    #        have_access = self.have_access(obj)
    #
    #        for obj in have_access:
    #            if isinstance(obj, User):
    #                yield 'user_%i' % obj.id
    #            elif isinstance(obj, Group):
    #                yield 'group_%i' % obj.id
    #
    #    return list(_access_iter(obj))


class conceptIndex(baseObjectIndex):
    statuses = indexes.MultiValueField(faceted=True)
    highest_state = indexes.IntegerField()
    ra_statuses = indexes.MultiValueField()
    registrationAuthorities = indexes.MultiValueField(faceted=True)
    workgroup = indexes.IntegerField(faceted=True)
    is_public = indexes.BooleanField()
    restriction = indexes.IntegerField(faceted=True)
    version = indexes.CharField(model_attr="version")
    submitter_id = indexes.IntegerField(model_attr="submitter_id", null=True)
    facet_model_ct = indexes.IntegerField(faceted=True)

    template_name = "search/searchItem.html"

    def prepare_registrationAuthorities(self, obj):
        ras_stats = [str(s.registrationAuthority.id) for s in obj.current_statuses().all()]
        ras_reqs = [str(rr.registration_authority.id) for rr in obj.review_requests.filter(~Q(status=models.REVIEW_STATES.cancelled)).all()]

        return list(set(ras_stats + ras_reqs))

    def prepare_is_public(self, obj):
        return obj.is_public()

    def prepare_workgroup(self, obj):
        if obj.workgroup:
            return int(obj.workgroup.id)
        else:
            return -99

    def prepare_statuses(self, obj):
        # We don't remove duplicates as it should mean the more standard it is the higher it will rank
        states = [int(s.state) for s in obj.current_statuses().all()]
        if not states:
            states = ['-99']  # This is an unregistered item
        return states

    def prepare_highest_state(self, obj):
        # Include -99, so "unregistered" items get a value
        state = max([int(s.state) for s in obj.current_statuses().all()] + [-99])
        """
        We don't want retired or superseded ranking higher than standards during search
        as these are no longer "fit for purpose" so we'll place them below other
        states for the purposes of sorting in search.
        """
        if state == models.STATES.retired:
            state = -10
        elif state == models.STATES.superseded:
            state = -9
        return state

    def prepare_ra_statuses(self, obj):
        # This allows us to check a registration authority and a state simultaneously
        states = [
            "%s___%s" % (str(s.registrationAuthority.id), str(s.state)) for s in obj.current_statuses().all()
        ]
        return states

    def prepare_facet_model_ct(self, obj):
        # We need to use the content type, as if we use text it gets stemmed wierdly
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(obj)
        return ct.pk

    def prepare_restriction(self, obj):
        if obj._is_public:
            return RESTRICTION['Public']
        elif obj._is_locked:
            return RESTRICTION['Locked']
        return RESTRICTION['Unlocked']
