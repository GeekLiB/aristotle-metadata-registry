from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse, Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.views.generic import ListView, TemplateView, DetailView, FormView

from aristotle_mdr import models as MDR
from aristotle_mdr.contrib.links import forms as link_forms
from aristotle_mdr.contrib.links import models as link_models
from aristotle_mdr.contrib.links import perms

from formtools.wizard.views import SessionWizardView


class EditLinkFormView(FormView):
    template_name = "aristotle_mdr_links/actions/edit_link.html"
    form_class = link_forms.LinkEndEditor

    def dispatch(self, request, *args, **kwargs):
        self.link = get_object_or_404(
            link_models.Link, pk=self.kwargs['iid']
        )
        self.relation = self.link.relation
        if request.user.is_anonymous():
            return redirect(reverse('friendly_login') + '?next=%s' % request.path)
        if not perms.user_can_change_link(request.user, self.link):
            raise PermissionDenied
        return super(EditLinkFormView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(EditLinkFormView, self).get_form_kwargs()
        kwargs.update({
            'link': self.link,
            'roles': self.link.relation.relationrole_set.all(),
            'user': self.request.user
        })
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super(EditLinkFormView, self).get_context_data(*args, **kwargs)
        context.update(
            {
                'roles': self.link.relation.relationrole_set.all(),
                'link': self.link
            }
        )
        return context

    def get_success_url(self):
        next_url = self.request.GET.get('next', None)
        if next_url:
            return next_url
        else:
            return self.link.relation.get_absolute_url()

    @transaction.atomic
    def form_valid(self, form):
        role_concepts = form.cleaned_data
        roles = self.link.relation.relationrole_set.order_by('ordinal', 'name')

        for role in roles:
            concepts = role_concepts['role_' + str(role.pk)]
            try:
                concepts = list(concepts)
            except TypeError:
                concepts = [concepts]
            current_ends = link_models.LinkEnd.objects.filter(
                link=self.link,
                role=role
            )

            # Remove those that are deleted
            for end in current_ends:
                if end.concept_id not in [c.pk for c in concepts]:
                    end.delete()

            # Add those that are new
            for concept in concepts:
                if concept.pk not in [c.concept_id for c in current_ends]:
                    link_models.LinkEnd.objects.create(link=self.link, role=role, concept=concept)

        return HttpResponseRedirect(self.get_success_url())


class AddLinkWizard(SessionWizardView):
    form_list = base_form_list = [
        link_forms.AddLink_SelectRelation_1,
        link_forms.AddLink_SelectConcepts_2,
        link_forms.AddLink_Confirm_3,
    ]
    base_form_count = len(form_list)
    template_names = [
        "aristotle_mdr_links/actions/add_link_wizard_1_select_relation.html",
        "aristotle_mdr_links/actions/add_link_wizard_2_select_concepts.html",
        "aristotle_mdr_links/actions/add_link_wizard_3_confirm.html"
    ]

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_anonymous():
            return redirect(reverse('friendly_login') + '?next=%s' % request.path)
        if not request.user.has_perm('aristotle_mdr_links.add_link'):
            raise PermissionDenied
        return super(AddLinkWizard, self).dispatch(request, *args, **kwargs)

    def get_template_names(self):
        return self.template_names[int(self.steps.current)]

    def get_roles(self):
        self.relation = self.get_cleaned_data_for_step('0')['relation']
        return self.relation.relationrole_set.order_by('ordinal', 'name')

    def get_form_kwargs(self, step):
        kwargs = super(AddLinkWizard, self).get_form_kwargs(step)
        if int(step) == 0:
            kwargs.update({
                'user': self.request.user
            })
        if int(step) == 1:
            self.relation = self.get_cleaned_data_for_step('0')['relation']
            kwargs.update({
                'roles': self.relation.relationrole_set.all(),
                'user': self.request.user
            })

        return kwargs

    def get_role_concepts(self):
        role_concepts = []
        for role, concepts in zip(self.get_roles(), self.get_cleaned_data_for_step('1').values()):
            if role.multiplicity == 1:
                concepts = [concepts]
            role_concepts.append((role, concepts))
        print(role_concepts)
        return role_concepts

    def get_context_data(self, *args, **kwargs):
        context = super(AddLinkWizard, self).get_context_data(*args, **kwargs)
        if int(self.steps.current) == 1:
            context.update({'roles': self.get_roles()})
        if int(self.steps.current) == 2:

            context.update({
                'relation': self.get_cleaned_data_for_step('0')['relation'],
                'role_concepts': self.get_role_concepts()
            })
        return context

    @transaction.atomic
    def done(self, *args, **kwargs):
        self.relation = self.get_cleaned_data_for_step('0')['relation']
        role_concepts = self.get_cleaned_data_for_step('1')

        link = link_models.Link.objects.create(relation=self.relation)
        for role, concepts in self.get_role_concepts():
            # if role.multiplicity == 1:
            #     concepts = [concepts]
            for concept in concepts:
                link_models.LinkEnd.objects.create(link=link, role=role, concept=concept)

        return HttpResponseRedirect(
            self.request.GET.get('next', self.relation.get_absolute_url())
        )


def link_json_for_item(request, iid):
    item = get_object_or_404(MDR._concept, pk=iid).item
    links = link_models.Link.objects.filter(linkend__concept=item).all().distinct()

    nodes = []
    edges = []
    for link in links:
        for end in link.linkend_set.all():
            if 'concept_%s' % end.concept.id not in [i['id'] for i in nodes]:
                if end.concept == item.concept:
                    nodes.append({
                        'id': 'concept_%s' % end.concept.id,
                        'label': end.concept.name,
                        'group': 'active',
                        'title': "<i>This item</i>",
                    })
                else:
                    nodes.append({
                        'id': 'concept_%s' % end.concept.id,
                        'label': end.concept.name,
                        'group': 'regular',
                        'title': '<a href="%s">%s</a>' % (end.concept.get_absolute_url(), end.concept.name),
                    })
            if end.concept == item.concept:
                edges.append({
                    'to': 'link_%s_%s' % (link.relation.id, link.id),
                    'from': 'concept_%s' % end.concept.id,
                    # 'label': end.role.name
                })
            else:
                edges.append({
                    'from': 'link_%s_%s' % (link.relation.id, link.id),
                    'to': 'concept_%s' % end.concept.id,
                    # 'label': end.role.name
                    'title': end.role.name
                })
        if 'link_%s_%s' % (link.relation.id, link.id) not in [i['id'] for i in nodes]:
            nodes.append({
                'id': 'link_%s_%s' % (link.relation.id, link.id),
                'label': link.relation.name,
                'group': 'relation',
                'title': '<a href="%s">%s</a>' % (link.relation.get_absolute_url(), link.relation.definition),
            })

    return JsonResponse({
        'nodes': nodes,
        'edges': edges,
    })
