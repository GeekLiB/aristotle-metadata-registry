from django import forms
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

import aristotle_mdr.models as MDR
from aristotle_mdr.forms.creation_wizards import UserAwareModelForm, UserAwareForm
from aristotle_mdr.forms import ChangeStatusForm
from bootstrap3_datetime.widgets import DateTimePicker


class RequestReviewForm(UserAwareModelForm):
    registration_date = forms.DateField(
        required=False,
        label=_("Registration date"),
        widget=DateTimePicker(options={"format": "YYYY-MM-DD"}),
        initial=timezone.now()
    )

    class Meta:
        model = MDR.ReviewRequest
        fields = [
            'state', 'registration_authority', 'message',
            'registration_date', 'cascade_registration'
        ]


class RequestReviewCancelForm(UserAwareModelForm):
    class Meta:
        model = MDR.ReviewRequest
        fields = []


class RequestReviewRejectForm(UserAwareModelForm):
    class Meta:
        model = MDR.ReviewRequest
        fields = ['response']


class RequestReviewAcceptForm(UserAwareForm):
    response = forms.CharField(
        max_length=512,
        required=False,
        label=_("Reply to the original review request below."),
        widget=forms.Textarea
    )
