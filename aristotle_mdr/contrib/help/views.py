from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.views.generic import ListView, TemplateView, DetailView

from aristotle_mdr.contrib.help.models import ConceptHelp, HelpPage, HelpBase
from aristotle_mdr.utils import get_concepts_for_apps


class AppHelpViewer(DetailView):
    def get_context_data(self, **kwargs):
        context = super(AppHelpViewer, self).get_context_data(**kwargs)
        if self.object.app_label:
            self.app = self.object.app_label
            context['app'] = apps.get_app_config(self.app)
        return context


class AllHelpView(ListView):
    template_name = "aristotle_mdr_help/all_help.html"
    model = HelpPage


class AllConceptHelpView(ListView):
    template_name = "aristotle_mdr_help/all_concept_help.html"
    model = ConceptHelp


class ConceptAppHelpView(ListView):
    template_name = "aristotle_mdr_help/app_concept_help.html"

    def get_context_data(self, **kwargs):
        context = super(ConceptAppHelpView, self).get_context_data(**kwargs)
        context['app'] = apps.get_app_config(self.kwargs['app'])
        return context

    def get_queryset(self, *args, **kwargs):
        return ConceptHelp.objects.filter(app_label=self.kwargs['app'])


class HelpView(AppHelpViewer):
    template_name = "aristotle_mdr_help/regular_help.html"
    model = HelpPage


class ConceptHelpView(AppHelpViewer):
    template_name = "aristotle_mdr_help/concept_help.html"

    def get_object(self, queryset=None):
        app = self.kwargs['app']
        model = self.kwargs['model']
        return get_object_or_404(ConceptHelp, app_label=app, concept_type=model)

    def get_context_data(self, **kwargs):
        context = super(ConceptHelpView, self).get_context_data(**kwargs)

        model = self.kwargs['model']

        ct = ContentType.objects.get(app_label=self.app, model=model)
        context['model'] = ct.model_class()
        return context
