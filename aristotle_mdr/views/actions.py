from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.template import TemplateDoesNotExist
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView, DetailView
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
import datetime

import reversion

from aristotle_mdr import perms
from aristotle_mdr.utils import cache_per_item_user, concept_to_dict, construct_change_message, url_slugify_concept
from aristotle_mdr import forms as MDRForms
from aristotle_mdr import exceptions as registry_exceptions
from aristotle_mdr import models as MDR
from aristotle_mdr.forms import actions


class ItemSubpageView(object):
    def get_item(self):
        self.item = get_object_or_404(MDR._concept, pk=self.kwargs['iid']).item
        if not self.item.can_view(self.request.user):
            raise PermissionDenied
        return self.item

    def dispatch(self, *args, **kwargs):
        self.item = self.get_item()
        return super(ItemSubpageView, self).dispatch(*args, **kwargs)


class ItemSubpageFormView(ItemSubpageView, FormView):
    def get_context_data(self, *args, **kwargs):
        kwargs = super(ItemSubpageFormView, self).get_context_data(*args, **kwargs)
        kwargs['item'] = self.get_item()
        return kwargs


class SubmitForReviewView(ItemSubpageFormView):
    form_class = actions.RequestReviewForm
    template_name = "aristotle_mdr/actions/request_review.html"

    def get_context_data(self, *args, **kwargs):
        kwargs = super(SubmitForReviewView, self).get_context_data(*args, **kwargs)
        kwargs['reviews'] = self.get_item().review_requests.filter(status=MDR.REVIEW_STATES.submitted).all()
        return kwargs

    def get_form_kwargs(self):
        kwargs = super(SubmitForReviewView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        item = self.get_item()

        if form.is_valid():
            review = form.save(commit=False)
            review.requester = request.user
            review.save()
            review.concepts.add(item)
            message = mark_safe(
                _("<a href='{url}'>Review submitted, click to review</a>").format(url=reverse('aristotle_mdr:userReviewDetails', args=[review.pk]))
            )
            messages.add_message(request, messages.INFO, message)
            return HttpResponseRedirect(item.get_absolute_url())
        else:
            return self.form_invalid(form)


class ReviewActionMixin(object):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        review = self.get_review()
        if not perms.user_can_view_review(self.request.user, review):
            raise PermissionDenied
        if review.status != MDR.REVIEW_STATES.submitted:
            return HttpResponseRedirect(reverse('aristotle_mdr:userReviewDetails', args=[review.pk]))
        return super(ReviewActionMixin, self).dispatch(*args, **kwargs)

    def get_review(self):
        self.review = get_object_or_404(MDR.ReviewRequest, pk=self.kwargs['review_id'])
        return self.review

    def get_context_data(self, *args, **kwargs):
        kwargs = super(ReviewActionMixin, self).get_context_data(*args, **kwargs)
        kwargs['review'] = self.get_review()
        return kwargs

    def get_form_kwargs(self):
        kwargs = super(ReviewActionMixin, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class ReviewCancelView(ReviewActionMixin, FormView):
    form_class = actions.RequestReviewCancelForm
    template_name = "aristotle_mdr/user/user_request_cancel.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        review = self.get_review()
        if not self.request.user == review.requester:
            raise PermissionDenied
        if review.status != MDR.REVIEW_STATES.submitted:
            return HttpResponseRedirect(reverse('aristotle_mdr:userReviewDetails', args=[review.pk]))

        return super(ReviewCancelView, self).dispatch(*args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(ReviewCancelView, self).get_form_kwargs()
        kwargs['instance'] = self.get_review()
        return kwargs

    def post(self, request, *args, **kwargs):
        form = self.get_form()

        if form.is_valid():
            review = form.save(commit=False)
            review.status = MDR.REVIEW_STATES.cancelled
            review.save()
            message = _("Review successfully cancelled")
            messages.add_message(request, messages.INFO, message)
            return HttpResponseRedirect(reverse('aristotle_mdr:userMyReviewRequests'))
        else:
            return self.form_invalid(form)


class ReviewRejectView(ReviewActionMixin, FormView):
    form_class = actions.RequestReviewRejectForm
    template_name = "aristotle_mdr/user/user_request_reject.html"

    def get_form_kwargs(self):
        kwargs = super(ReviewRejectView, self).get_form_kwargs()
        kwargs['instance'] = self.get_review()
        return kwargs

    def post(self, request, *args, **kwargs):
        form = self.get_form()

        if form.is_valid():
            review = form.save(commit=False)
            review.reviewer = request.user
            review.status = MDR.REVIEW_STATES.rejected
            review.save()
            message = _("Review successfully rejected")
            messages.add_message(request, messages.INFO, message)
            return HttpResponseRedirect(reverse('aristotle_mdr:userReadyForReview'))
        else:
            return self.form_invalid(form)


class ReviewAcceptView(ReviewActionMixin, FormView):
    form_class = actions.RequestReviewAcceptForm
    template_name = "aristotle_mdr/user/user_request_accept.html"

    def get_context_data(self, *args, **kwargs):
        from aristotle_mdr.views.utils import generate_visibility_matrix
        kwargs = super(ReviewAcceptView, self).get_context_data(*args, **kwargs)
        import json
        kwargs['status_matrix'] = json.dumps(generate_visibility_matrix(self.request.user))
        return kwargs

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        review = self.get_review()

        if form.is_valid():

            message = self.register_items(form)

            review.reviewer = request.user
            review.response = form.cleaned_data['response']
            review.status = MDR.REVIEW_STATES.accepted
            review.save()

            messages.add_message(request, messages.INFO, message)
            return HttpResponseRedirect(reverse('aristotle_mdr:userReadyForReview'))
        else:
            return self.form_invalid(form)

    def register_items(self, form):
        review = self.get_review()
        ras = [review.registration_authority]  # Make into an iterable, as this may change in future
        state = review.state
        regDate = review.registration_date
        cascade = review.cascade_registration
        changeDetails = review.message

        items = review.concepts.all()
        with transaction.atomic(), reversion.revisions.create_revision():
            reversion.revisions.set_user(self.request.user)
            success = []
            failed = []
            if regDate is None:
                regDate = timezone.now().date()
            for item in items:

                for ra in ras:
                    if cascade:
                        register_method = ra.cascaded_register
                    else:
                        register_method = ra.register

                    r = register_method(
                        item,
                        state,
                        self.request.user,
                        changeDetails=changeDetails,
                        registrationDate=regDate,
                    )
                    for f in r['failed']:
                        failed.append(f)
                    for s in r['success']:
                        success.append(s)
            failed = list(set(failed))
            success = list(set(success))
            bad_items = sorted([str(i.id) for i in failed])
            if failed:
                message = _(
                    "%(num_items)s items registered in %(num_ra)s registration authorities. \n"
                    "%(num_faileds)s items failed, they had the id's: %(bad_ids)s"
                ) % {
                    'num_items': len(items),
                    'num_ra': len(ras),
                    'num_faileds': len(failed),
                    'bad_ids': ",".join(bad_items)
                }
            else:
                message = _(
                    "%(num_items)s items registered in %(num_ra)s registration authorities. \n"
                ) % {
                    'num_items': len(items),
                    'num_ra': len(ras),
                }

            reversion.revisions.set_comment(message)
            return message


class CheckCascadedStates(ItemSubpageView, DetailView):
    pk_url_kwarg = 'iid'
    context_object_name = 'item'
    queryset = MDR._concept.objects.all()
    template_name = 'aristotle_mdr/actions/check_states.html'

    def dispatch(self, *args, **kwargs):
        self.item = self.get_item()
        if not self.item.item.registry_cascade_items:
            raise Http404
        return super(CheckCascadedStates, self).dispatch(*args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        kwargs = super(CheckCascadedStates, self).get_context_data(*args, **kwargs)

        state_matrix = [
            # (item,[(states_ordered_alphabetically_by_ra_as_per_parent_item,state_of_parent_with_same_ra)],[extra statuses] )
            ]
        item = self.get_item()
        states = []
        ras = []
        for s in item.current_statuses():
            if s.registrationAuthority not in ras:
                ras.append(s.registrationAuthority)
                states.append(s)

        for i in item.item.registry_cascade_items:
            sub_states = [(None, None)] * len(ras)
            extras = []
            for s in i.current_statuses():
                ra = s.registrationAuthority
                if ra in ras:
                    sub_states[ras.index(ra)] = (s, states[ras.index(ra)])
                else:
                    extras.append(s)
            state_matrix.append((i, sub_states, extras))

        kwargs['known_states'] = states
        kwargs['state_matrix'] = state_matrix
        return kwargs
