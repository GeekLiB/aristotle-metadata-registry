from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldError
from django.db.models import Q
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic import ListView, TemplateView
from aristotle_mdr.utils import get_concepts_for_apps, fetch_aristotle_settings
from collections import OrderedDict


class BrowseApps(TemplateView):
    template_name = "aristotle_mdr_browse/apps_list.html"
    ordering = 'app_label'

    def get_context_data(self, *args, **kwargs):
        context = super(BrowseApps, self).get_context_data(*args, **kwargs)

        aristotle_apps = fetch_aristotle_settings().get('CONTENT_EXTENSIONS', [])
        aristotle_apps += ["aristotle_mdr"]
        out = {}

        for m in get_concepts_for_apps(aristotle_apps):
            # Only output subclasses of 11179 concept
            app_models = out.get(m.app_label, {'app': None, 'models': []})
            if app_models['app'] is None:
                app_models['app'] = getattr(
                    apps.get_app_config(m.app_label),
                    'verbose_name',
                    _("No name")  # Where no name is configured in the app_config, set a dummy so we don't keep trying
                )

            app_models['models'].append(m)
            out[m.app_label] = app_models

        context['apps'] = OrderedDict(sorted(out.items(), key=lambda app: app[1]['app']))
        return context


class AppBrowser(ListView):
    def get_context_data(self, *args, **kwargs):
        # Call the base implementation first to get a context
        context = super(AppBrowser, self).get_context_data(*args, **kwargs)
        context['app_label'] = self.kwargs['app']
        context['app'] = apps.get_app_config(self.kwargs['app'])
        return context


class BrowseModels(AppBrowser):
    template_name = "aristotle_mdr_browse/model_list.html"
    context_object_name = "model_list"
    paginate_by = 25

    def get_queryset(self):
        app = self.kwargs['app']
        return get_concepts_for_apps([app])


class BrowseConcepts(AppBrowser):
    _model = None
    paginate_by = 25

    @property
    def model(self):
        if self._model is None:
            app = self.kwargs['app']
            model = self.kwargs['model']
            ct = ContentType.objects.filter(app_label=app, model=model)
            if not ct:
                raise Http404
            else:
                self._model = ct.first().model_class()
        return self._model

    def get_queryset(self, *args, **kwargs):
        queryset = super(BrowseConcepts, self).get_queryset(*args, **kwargs)

        # Regular queryset filter
        for f in self.request.GET.getlist('f'):
            try:
                k, v = f.split(':', 1)
                queryset = queryset.filter(**{k: v})
            except:
                pass

        # Regular queryset filters
        filters = {}
        for f in self.request.GET.getlist('f'):
            if ':' in f:
                k, v = f.split(':', 1)
                filter_vals = filters.get(k, [])
                filter_vals.append(v)
                filters[k] = filter_vals

        for query, values in filters.items():
            try:
                k = "%s__in" % k
                queryset = queryset.filter(**{k: values})
            except FieldError:
                pass

        # slot filters
        slots = {}
        for sf in self.request.GET.getlist('sf'):
            if ':' in sf:
                k, v = sf.split(':', 1)
                slot_vals = slots.get(k, [])
                slot_vals.append(v)
                slots[k] = slot_vals

        for slot_name, values in slots.items():
            try:
                queryset = queryset.filter(
                    slots__name=slot_name,
                    slots__value__in=values,
                )
            except FieldError:
                pass

        return queryset.visible(self.request.user)

    def get_context_data(self, *args, **kwargs):
        # Call the base implementation first to get a context
        context = super(BrowseConcepts, self).get_context_data(*args, **kwargs)
        context['model'] = self.model
        context['model_name'] = self.model._meta.model_name
        context['sort'] = self.order
        return context

    def get_template_names(self):
        app_label = self.kwargs['app']
        names = super(BrowseConcepts, self).get_template_names()
        names.append('aristotle_mdr_browse/list.html')
        names.insert(0, 'aristotle_mdr_browse/%s/%s_list.html' % (app_label, self.model._meta.model_name))
        return names

    def get_ordering(self):
        from aristotle_mdr.views.utils import paginate_sort_opts
        self.order = self.request.GET.get('sort', 'name_asc')
        return paginate_sort_opts.get(self.order)
