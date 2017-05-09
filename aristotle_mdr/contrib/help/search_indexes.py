import datetime
import haystack.indexes as indexes

from aristotle_mdr.contrib.help import models
from django.template import TemplateDoesNotExist
from django.utils import timezone
from aristotle_mdr.search_indexes import RESTRICTION


class HelpObjectIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, use_template=True)
    modified = indexes.DateTimeField(model_attr='modified')
    created = indexes.DateTimeField(model_attr='created')
    name = indexes.CharField(model_attr='title')
    facet_model_ct = indexes.IntegerField(faceted=True)
    is_public = indexes.BooleanField(model_attr='is_public')

    restriction = indexes.IntegerField(faceted=True)

    def get_model(self):
        raise NotImplementedError  # pragma: no cover -- This should always be overridden

    # From http://unfoldthat.com/2011/05/05/search-with-row-level-permissions.html
    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""

        return self.get_model().objects.filter(modified__lte=timezone.now())

    def prepare_restriction(self, obj):
        return RESTRICTION['Public']

    def prepare_facet_model_ct(self, obj):
        # We need to use the content type, as if we use text it gets stemmed wierdly
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(obj)
        return ct.pk


class ConceptHelpIndex(HelpObjectIndex, indexes.Indexable):
    template_name = "search/searchConceptHelp.html"

    def get_model(self):
        return models.ConceptHelp


class HelpPageIndex(HelpObjectIndex, indexes.Indexable):
    template_name = "search/searchHelpPage.html"

    def get_model(self):
        return models.HelpPage
