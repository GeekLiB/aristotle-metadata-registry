import datetime
from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.apps import apps
from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices

from haystack import connections
from haystack.constants import DEFAULT_ALIAS
from haystack.forms import SearchForm, FacetedSearchForm
from haystack.query import EmptySearchQuerySet, SearchQuerySet, SQ

from bootstrap3_datetime.widgets import DateTimePicker

import aristotle_mdr.models as MDR
from aristotle_mdr.widgets import (
    BootstrapDropdownSelectMultiple, BootstrapDropdownIntelligentDate,
    BootstrapDropdownSelect, BootstrapDateTimePicker
)
from aristotle_mdr.utils import fetch_aristotle_settings


QUICK_DATES = Choices(
    ('', 'anytime', _('Any time')),
    ('h', 'hour', _('Last hour')),
    ('t', 'today', _('Today')),
    ('w', 'week', _('This week')),
    ('m', 'month', _('This month')),
    ('y', 'year', _('This year')),
    ('X', 'custom', _('Custom period')),
)


SORT_OPTIONS = Choices(
    ('n', 'natural', _('Ranking')),
    ('ma', 'modified_ascending', _('Modified ascending')),
    ('md', 'modified_descending', _('Modified descending')),
    ('ma', 'created_ascending', _('Created ascending')),
    ('md', 'created_descending', _('Created descending')),
    ('aa', 'alphabetical', _('Alphabetical')),
    ('s', 'state', _('Registration state')),
)


# This function is not critical and are mathematically sound, so testing is not required.
def time_delta(delta):  # pragma: no cover
    """
    Datetimes are expensive to search on, so this function gives approximations of the time options.
    Absolute precision can be used using the custom ranges, but may be slower.
    These approximations mean that similar ranges can be used in the haystack index when searching.
    """
    if delta == QUICK_DATES.hour:
        """
        The last hour, actually translates to the begin of the last hour, so
        this returns objects between 60 and 119 mintues ago.
        """
        n = datetime.datetime.now()
        n = datetime.datetime.combine(n.date(), datetime.time(hour=n.time().hour))
        return n - datetime.timedelta(hours=1)
    elif delta == QUICK_DATES.today:
        """
        Today returns everything today.
        """
        return datetime.date.today()  # - datetime.timedelta(days=1)
    elif delta == QUICK_DATES.week:
        """
        This week is pretty straight forward. SSReturns 7 days ago from the *beginning* of today.
        """
        return datetime.date.today() - datetime.timedelta(days=7)
    elif delta == QUICK_DATES.month:
        """
        This goes back to this day last month, and then finds the prior day thats
        divisible by 7 (not less than 1).
          1-6 -> 1
         7-13 -> 7
        14-20 -> 14
        21-27 -> 21
        28-31 -> 28
        """
        t = datetime.date.today()
        last_month = datetime.date(day=1, month=t.month, year=t.year) - datetime.timedelta(days=1)
        days = max(((t.day) // 7) * 7, 1)
        last_month = datetime.date(day=days, month=last_month.month, year=last_month.year)
        return datetime.date(day=1, month=last_month.month, year=last_month.year)
    elif delta == QUICK_DATES.year:
        """
        This goes back to the beginning of this month last year.
        So it searchs from the first of this month, last year.
        """
        t = datetime.date.today()
        return datetime.date(day=1, month=t.month, year=(t.year - 1))
    return None
DELTA = {
    QUICK_DATES.hour: datetime.timedelta(hours=1),
    QUICK_DATES.today: datetime.timedelta(days=1),
    QUICK_DATES.week: datetime.timedelta(days=7),
    QUICK_DATES.month: datetime.timedelta(days=31),
    QUICK_DATES.year: datetime.timedelta(days=366)
}


def first_letter(j):
    """Extract the first letter of a string"""
    # Defined as a method rather than using a lambda to keep a style guide happy.
    return j[0]


class EmptyPermissionSearchQuerySet(EmptySearchQuerySet):
    # Just like a Haystack EmptySearchQuerySet, this behaves like a PermissionsSearchQuerySet
    # But returns nothing all the time.
    def apply_permission_checks(self, user=None, public_only=False, user_workgroups_only=False):
        return self

    def apply_registration_status_filters(self, *args, **kwargs):
        return self


class PermissionSearchQuerySet(SearchQuerySet):
    def models(self, *mods):
        # We have to redefine this because Whoosh & Haystack don't play well with model filtering
        from haystack.utils import get_model_ct
        mods = [get_model_ct(m) for m in mods]
        return self.filter(django_ct__in=mods)

    def apply_permission_checks(self, user=None, public_only=False, user_workgroups_only=False):
        sqs = self
        q = SQ(is_public=True)
        if user is None or user.is_anonymous():
            # Regular users can only see public items, so boot them off now.
            sqs = sqs.filter(q)
            return sqs

        q |= SQ(submitter_id=user.pk)  # users can see items they create
        if user.is_superuser:
            q = SQ()  # Super-users can see everything
        else:
            # Non-registrars can only see public things or things in their workgroup
            # if they have no workgroups they won't see anything extra
            if user.profile.workgroups.count() > 0:
                # for w in user.profile.workgroups.all():
                #    q |= SQ(workgroup=str(w.id))
                q |= SQ(workgroup__in=[int(w.id) for w in user.profile.workgroups.all()])
            if user.profile.is_registrar:
                # if registrar, also filter through items in the registered in their authorities
                q |= SQ(registrationAuthorities__in=[str(r.id) for r in user.profile.registrarAuthorities])
        if public_only:
            q &= SQ(is_public=True)
        if user_workgroups_only:
            q &= SQ(workgroup__in=[str(w.id) for w in user.profile.workgroups.all()])

        if q:
            sqs = sqs.filter(q)
        return sqs

    def apply_registration_status_filters(self, states=[], ras=[]):
        sqs = self
        if states and not ras:
            states = [int(s) for s in states]
            sqs = sqs.filter(statuses__in=states)
        elif ras and not states:
            ras = [ra for ra in ras]
            sqs = sqs.filter(registrationAuthorities__in=ras)
        elif states and ras:
            # If we have both states and ras, merge them so we only search for
            # items with those statuses in those ras
            terms = ["%s___%s" % (str(r), str(s)) for r in ras for s in states]
            sqs = sqs.filter(ra_statuses__in=terms)
        return sqs


class TokenSearchForm(FacetedSearchForm):
    token_models = []
    kwargs = {}

    def prepare_tokens(self):
        try:
            query = self.cleaned_data.get('q')
        except:
            return {}
        opts = connections[DEFAULT_ALIAS].get_unified_index().fields.keys()
        kwargs = {}
        query_text = []
        token_models = []
        for word in query.split(" "):
            if ":" in word:
                opt, arg = word.split(":", 1)
                if opt in opts:
                    kwargs[str(opt)]=arg
                elif opt == "type":
                    # we'll allow these through and assume they meant content type
                    from django.conf import settings
                    aristotle_apps = fetch_aristotle_settings().get('CONTENT_EXTENSIONS', [])
                    aristotle_apps += ["aristotle_mdr"]

                    from django.contrib.contenttypes.models import ContentType
                    arg = arg.lower().replace('_', '').replace('-', '')
                    mods = ContentType.objects.filter(app_label__in=aristotle_apps).all()
                    for i in mods:
                        if hasattr(i.model_class(), 'get_verbose_name'):
                            model_short_code = "".join(
                                map(
                                    first_letter, i.model_class()._meta.verbose_name.split(" ")
                                )
                            ).lower()
                            if arg == model_short_code:
                                token_models.append(i.model_class())
                        if arg == i.model:
                            token_models.append(i.model_class())

            else:
                query_text.append(word)
        self.token_models = token_models
        self.query_text = " ".join(query_text)
        self.kwargs = kwargs
        return kwargs

    def search(self):
        self.query_text = None
        kwargs = self.prepare_tokens()
        if not self.is_valid():
            return self.no_query_found()

        if not self.cleaned_data.get('q'):
            return self.no_query_found()

        if self.query_text:
            sqs = self.searchqueryset.auto_query(self.query_text)
        else:
            sqs = self.searchqueryset

        if self.token_models:
            sqs = sqs.models(*self.token_models)
        if kwargs:
            sqs = sqs.filter(**kwargs)

        if self.load_all:
            sqs = sqs.load_all()

        return sqs

    def no_query_found(self):
        return EmptyPermissionSearchQuerySet()

datePickerOptions = {
    "format": "YYYY-MM-DD",
    # "pickTime": False,
    # "pickDate": True,
    "defaultDate": "",
    "useCurrent": False,
}


class PermissionSearchForm(TokenSearchForm):
    """
        We need to make a new form as permissions to view objects are a bit finicky.
        This form allows us to perform the base query then restrict it to just those
        of interest.

        TODO: This might not scale well, so it may need to be looked at in production.
    """
    mq=forms.ChoiceField(
        required=False,
        initial=QUICK_DATES.anytime,
        choices=QUICK_DATES,
        widget=BootstrapDropdownIntelligentDate
    )
    mds = forms.DateField(
        required=False,
        label="Modified after date",
        widget=BootstrapDateTimePicker(options=datePickerOptions)
    )
    mde = forms.DateField(
        required=False,
        label="Modified before date",
        widget=BootstrapDateTimePicker(options=datePickerOptions)
    )
    cq=forms.ChoiceField(
        required=False,
        initial=QUICK_DATES.anytime,
        choices=QUICK_DATES,
        widget=BootstrapDropdownIntelligentDate
    )
    cds = forms.DateField(
        required=False,
        label="Created after date",
        widget=BootstrapDateTimePicker(options=datePickerOptions)
    )
    cde = forms.DateField(
        required=False,
        label="Created before date",
        widget=BootstrapDateTimePicker(options=datePickerOptions)
    )

    # Use short singular names
    # ras = [(ra.id, ra.name) for ra in MDR.RegistrationAuthority.objects.all()]
    ra = forms.MultipleChoiceField(
        required=False, label=_("Registration authority"),
        choices=[], widget=BootstrapDropdownSelectMultiple
    )

    sort = forms.ChoiceField(
        required=False, initial=SORT_OPTIONS.natural,
        choices=SORT_OPTIONS, widget=BootstrapDropdownSelect
    )
    from aristotle_mdr.search_indexes import BASE_RESTRICTION
    res = forms.ChoiceField(
        required=False, initial=None,
        choices=BASE_RESTRICTION.items(),
        label="Item visibility state"
    )

    state = forms.MultipleChoiceField(
        required=False,
        label=_("Registration status"),
        choices=MDR.STATES + [(-99, _('Unregistered'))],  # Allow unregistered as a selection
        widget=BootstrapDropdownSelectMultiple
    )
    public_only = forms.BooleanField(
        required=False,
        label="Only show public items"
    )
    myWorkgroups_only = forms.BooleanField(
        required=False,
        label="Only show items in my workgroups"
    )
    models = forms.MultipleChoiceField(
        choices=[],  # model_choices(),
        required=False, label=_('Item type'),
        widget=BootstrapDropdownSelectMultiple
    )
    # F for facet!
    # searchqueryset = PermissionSearchQuerySet

    def __init__(self, *args, **kwargs):
        if 'searchqueryset' not in kwargs.keys() or kwargs['searchqueryset'] is None:
            kwargs['searchqueryset'] = PermissionSearchQuerySet()
        if not issubclass(type(kwargs['searchqueryset']), PermissionSearchQuerySet):
            raise ImproperlyConfigured("Aristotle Search Queryset connection must be a subclass of PermissionSearchQuerySet")
        super(PermissionSearchForm, self).__init__(*args, **kwargs)

        from haystack.forms import SearchForm, FacetedSearchForm, model_choices

        self.fields['ra'].choices = [(ra.id, ra.name) for ra in MDR.RegistrationAuthority.objects.all()]
        self.fields['models'].choices = model_choices()

    def get_models(self):
        """Return an alphabetical list of model classes in the index."""
        search_models = []

        if self.is_valid() and self.cleaned_data['models']:
            for model in self.cleaned_data['models']:
                search_models.append(apps.get_model(*model.split('.')))

        return search_models

    filters = "models mq cq cds cde mds mde state ra res".split()

    @property
    def applied_filters(self):
        if not hasattr(self, 'cleaned_data'):
            return []
        return [f for f in self.filters if self.cleaned_data.get(f, False)]

    def search(self, repeat_search=False):
        # First, store the SearchQuerySet received from other processing.
        sqs = super(PermissionSearchForm, self).search()
        if not self.token_models and self.get_models():
            sqs = sqs.models(*self.get_models())
        self.repeat_search = repeat_search

        has_filter = self.kwargs or self.token_models or self.applied_filters
        if not has_filter and not self.query_text:
            return self.no_query_found()

        if self.applied_filters and not self.query_text:  # and not self.kwargs:
            # If there is a filter, but no query then we'll force some results.
            sqs = self.searchqueryset.order_by('-modified')
            self.filter_search = True
            self.attempted_filter_search = True

        states = self.cleaned_data.get('state', None)
        ras = self.cleaned_data.get('ra', None)
        restriction = self.cleaned_data['res']
        sqs = sqs.apply_registration_status_filters(states, ras)

        if restriction:
            sqs = sqs.filter(restriction=restriction)

        sqs = self.apply_date_filtering(sqs)
        sqs = sqs.apply_permission_checks(
            user=self.request.user,
            public_only=self.cleaned_data['public_only'],
            user_workgroups_only=self.cleaned_data['myWorkgroups_only']
        )

        extra_facets_details = {}
        facets_opts = self.request.GET.getlist('f', [])

        for _facet in facets_opts:
            _facet, value = _facet.split("::", 1)
            # Force exact as otherwise we don't match when there are spaces.
            # Insensitive to improve matching
            sqs = sqs.filter(**{"%s__iexact" % _facet: value})
            facets_details = extra_facets_details.get(_facet, {'applied': []})
            facets_details['applied'] = list(set(facets_details['applied'] + [value]))
            extra_facets_details[_facet] = facets_details

        self.has_spelling_suggestions = False
        if not self.repeat_search:

            if sqs.count() < 5:
                self.check_spelling(sqs)

            if sqs.count() == 0:
                if sqs.count() == 0 and self.has_spelling_suggestions:
                    self.auto_correct_spell_search = True
                    self.cleaned_data['q'] = self.suggested_query
                elif has_filter and self.cleaned_data['q']:
                    # If there are 0 results with a search term, and filters applied
                    # lets be nice and remove the filters and try again.
                    # There will be a big message on the search page that says what we did.
                    for f in self.filters:
                        self.cleaned_data[f] = None
                    self.auto_broaden_search = True
                # Re run the query with the updated details
                sqs = self.search(repeat_search=True)
            # Only apply sorting on the first pass through
            sqs = self.apply_sorting(sqs)

        # Don't applying sorting on the facet as ElasticSearch2 doesn't like this.
        filters_to_facets = {
            'ra': 'registrationAuthorities',
            'models': 'facet_model_ct',
            'state': 'statuses',
        }
        for _filter, facet in filters_to_facets.items():
            if _filter not in self.applied_filters:
                # Don't do this: sqs = sqs.facet(facet, sort='count')
                sqs = sqs.facet(facet)

        logged_in_facets = {
            'wg': 'workgroup',
            'res': 'restriction'
        }
        if self.request.user.is_active:
            for _filter, facet in logged_in_facets.items():
                if _filter not in self.applied_filters:
                    # Don't do this: sqs = sqs.facet(facet, sort='count')
                    sqs = sqs.facet(facet)

        extra_facets = []

        from aristotle_mdr.search_indexes import registered_indexes
        from haystack.fields import FacetField
        for model_index in registered_indexes:
            for name, field in model_index.fields.items():
                if field.faceted:
                    if name not in (list(filters_to_facets.values()) + list(logged_in_facets.values())):
                        extra_facets.append(name)

                        x = extra_facets_details.get(name, {})
                        x.update(**{
                            'title': getattr(field, 'title', name),
                            'display': getattr(field, 'display', None),
                            'allow_search': getattr(field, 'allow_search', False),
                        })
                        extra_facets_details[name]= x
                        # Don't do this: sqs = sqs.facet(facet, sort='count')  # Why Sam, why?
                        sqs = sqs.facet(name)

        self.facets = sqs.facet_counts()

        if 'fields' in self.facets:
            self.extra_facet_fields = [
                (k, {'values': sorted(v, key=lambda x: -x[1])[:10], 'details': extra_facets_details[k]})
                for k, v in self.facets['fields'].items()
                if k in extra_facets
            ]

            self.extra_facet_fields = [
                (k, {
                    'values': [
                        f for f in
                        sorted(v, key=lambda x: -x[1])
                        if f[0] not in extra_facets_details.get(k, {}).get('applied', [])
                        ][:10],
                    'details': extra_facets_details[k]
                })
                for k, v in self.facets['fields'].items()
                if k in extra_facets
            ]

            for facet, counts in self.facets['fields'].items():
                # Return the 5 top results for each facet in order of number of results.
                self.facets['fields'][facet] = sorted(counts, key=lambda x: -x[1])[:10]

        return sqs

    def check_spelling(self, sqs):
        if self.query_text:
            original_query = self.cleaned_data.get('q', "")

            try:  # Python 2
                from urllib import quote_plus
            except:  # Python 3
                from urllib.parse import quote_plus

            suggestions = []
            has_suggestions = False
            suggested_query = []

            # lets assume the words are ordered in importance
            # So we suggest words in order
            optimal_query = original_query
            for token in self.cleaned_data.get('q', "").split(" "):
                if token:  # remove blanks
                    suggestion = self.searchqueryset.spelling_suggestion(token)
                    if suggestion:
                        test_query = optimal_query.replace(token, suggestion)
                        # Haystack can *over correct* so we'll do a quick search with the
                        # suggested spelling to compare words against
                        try:
                            self.searchqueryset.auto_query(test_query)[0]
                            suggested_query.append(suggestion)
                            has_suggestions = True
                            optimal_query = test_query
                        except:
                            suggestion = None
                    else:
                        suggested_query.append(token)
                    suggestions.append((token, suggestion))
            if optimal_query != original_query:
                self.spelling_suggestions = suggestions
                self.has_spelling_suggestions = has_suggestions
                self.original_query = self.cleaned_data.get('q')
                self.suggested_query = quote_plus(' '.join(suggested_query), safe="")

    def apply_date_filtering(self, sqs):
        modify_quick_date = self.cleaned_data['mq']
        create_quick_date = self.cleaned_data['cq']
        create_date_start = self.cleaned_data['cds']
        create_date_end = self.cleaned_data['cde']
        modify_date_start = self.cleaned_data['mds']
        modify_date_end = self.cleaned_data['mde']

        """
        Modified filtering is really hard to do formal testing for as the modified
        dates are altered on save, so its impossible to alter the modified dates
        to check the search is working.
        However, this is the exact same process as creation date (which we can alter),
        so if creation filtering is working, modified filtering should work too.
        """
        if modify_quick_date and modify_quick_date is not QUICK_DATES.anytime:  # pragma: no cover
            delta = time_delta(modify_quick_date)
            if delta is not None:
                sqs = sqs.filter(modifed__gte=delta)
        elif modify_date_start or modify_date_end:  # pragma: no cover
            if modify_date_start:
                sqs = sqs.filter(modifed__gte=modify_date_start)
            if modify_date_end:
                sqs = sqs.filter(modifed__lte=modify_date_end)

        if create_quick_date and create_quick_date is not QUICK_DATES.anytime:
            delta = time_delta(create_quick_date)
            if delta is not None:
                sqs = sqs.filter(created__gte=delta)
        elif create_date_start or create_date_end:
            if create_date_start:
                sqs = sqs.filter(created__gte=create_date_start)
            if create_date_end:
                sqs = sqs.filter(created__lte=create_date_end)

        return sqs

    def apply_sorting(self, sqs):  # pragma: no cover, no security issues, standard Haystack methods, so already tested.
        sort_order = self.cleaned_data['sort']
        if sort_order == SORT_OPTIONS.modified_ascending:
            sqs = sqs.order_by('-modified')
        elif sort_order == SORT_OPTIONS.modified_descending:
            sqs = sqs.order_by('modified')
        elif sort_order == SORT_OPTIONS.created_ascending:
            sqs = sqs.order_by('-created')
        elif sort_order == SORT_OPTIONS.created_descending:
            sqs = sqs.order_by('created')
        elif sort_order == SORT_OPTIONS.alphabetical:
            sqs = sqs.order_by('name')
        elif sort_order == SORT_OPTIONS.state:
            sqs = sqs.order_by('-highest_state')

        return sqs
