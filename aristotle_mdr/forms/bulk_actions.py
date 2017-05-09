from django import forms
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import transaction
from django.forms import HiddenInput
from django.utils import timezone
from django.utils.html import mark_safe
from django.utils.translation import ugettext_lazy as _

from bootstrap3_datetime.widgets import DateTimePicker

import aristotle_mdr.models as MDR
from aristotle_mdr.forms import ChangeStatusForm
from aristotle_mdr.perms import (
    user_can_view,
    user_is_registrar,
    user_is_workgroup_manager,
    user_can_move_any_workgroup
)
from aristotle_mdr.forms.creation_wizards import UserAwareForm
from aristotle_mdr.contrib.autocomplete import widgets


class ForbiddenAllowedModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    def __init__(self, *args, **kwargs):
        self.validate_queryset = kwargs.pop('validate_queryset')
        super(ForbiddenAllowedModelMultipleChoiceField, self).__init__(*args, **kwargs)

    def _check_values(self, value):
        """
        Given a list of possible PK values, returns a QuerySet of the
        corresponding objects. Skips values if they are not in the queryset.
        This allows us to force a limited selection to the client, while
        ignoring certain additional values if given. However, this means
        *extra checking must be done* to limit over exposure and invalid
        data.
        """
        from django.core.exceptions import ValidationError
        from django.utils.encoding import force_text

        key = self.to_field_name or 'pk'
        # deduplicate given values to avoid creating many querysets or
        # requiring the database backend deduplicate efficiently.
        try:
            value = frozenset(value)
        except TypeError:
            # list of lists isn't hashable, for example
            raise ValidationError(
                self.error_messages['list'],
                code='list',
            )
        true_value = []
        for pk in value:
            try:
                self.validate_queryset.filter(**{key: pk})
            except (ValueError, TypeError):
                raise ValidationError(
                    self.error_messages['invalid_pk_value'],
                    code='invalid_pk_value',
                    params={'pk': pk},
                )
        qs = self.validate_queryset.filter(**{'%s__in' % key: value})
        pks = set(force_text(getattr(o, key)) for o in qs)
        for val in value:
            if force_text(val) not in pks:
                raise ValidationError(
                    self.error_messages['invalid_choice'],
                    code='invalid_choice',
                    params={'value': val},
                )
        return qs


class BulkActionForm(UserAwareForm):
    classes = ""
    confirm_page = None
    all_in_queryset = forms.BooleanField(
        label=_("All items"),
        required=False,
        widget=HiddenInput()
    )
    qs = forms.CharField(
        label=_("All items"),
        required=False,
        widget=HiddenInput()
    )

    # queryset is all as we try to be nice and process what we can in bulk
    # actions.
    items = ForbiddenAllowedModelMultipleChoiceField(
        queryset=MDR._concept.objects.all(),
        validate_queryset=MDR._concept.objects.all(),
        label="Related items",
        required=False,
    )
    items_label = "Select some items"
    queryset = MDR._concept.objects.all()

    def __init__(self, form, *args, **kwargs):
        initial_items = kwargs.pop('items', [])
        self.request = kwargs.pop('request')
        if 'user' in kwargs.keys():
            self.user = kwargs.get('user', None)
            queryset = MDR._concept.objects.visible(self.user)
        else:
            queryset = MDR._concept.objects.public()

        super(BulkActionForm, self).__init__(form, *args, **kwargs)

        self.fields['items'] = ForbiddenAllowedModelMultipleChoiceField(
            label=self.items_label,
            validate_queryset=MDR._concept.objects.all(),
            queryset=queryset,
            initial=initial_items,
            required=False,
            widget=widgets.ConceptAutocompleteSelectMultiple()
        )

    @property
    def items_to_change(self):
        if bool(self.cleaned_data.get('all_in_queryset', False)):
            filters = {}
            for v in self.cleaned_data.get('qs', "").split(','):
                if 'user' in v:
                    # if the queryset even contains a user, cut it right off
                    # otherwise, it could leak data if people tried to alter the query value
                    k = v.split('user', 1)[0] + 'user'
                    v = self.user
                else:
                    k, v = v.split('=', 1)
                filters.update({k: v})
            items = self.queryset.filter(**filters).visible(self.user)
        else:
            items = self.cleaned_data.get('items')
        return items

    @classmethod
    def can_use(cls, user):
        return True

    @classmethod
    def text(cls):
        if hasattr(cls, 'action_text'):
            return cls.action_text
        from django.utils.text import camel_case_to_spaces
        txt = cls.__name__
        txt = txt.replace('Form', '')
        txt = camel_case_to_spaces(txt)
        return txt


class LoggedInBulkActionForm(BulkActionForm):
    @classmethod
    def can_use(cls, user):
        return user.is_active


class AddFavouriteForm(LoggedInBulkActionForm):
    classes="fa-bookmark"
    action_text = _('Add favourite')
    items_label = "Items that will be added to your favourites list"

    def make_changes(self):
        items = self.items_to_change
        bad_items = [str(i.id) for i in items if not user_can_view(self.user, i)]
        items = items.visible(self.user)
        self.user.profile.favourites.add(*items)
        return _(
            "%(num_items)s items favourited. \n"
            "Some items failed, they had the id's: %(bad_ids)s"
        ) % {
            'num_items': len(items),
            'bad_ids': ",".join(bad_items)
        }


class RemoveFavouriteForm(LoggedInBulkActionForm):
    classes="fa-minus-square"
    action_text = _('Remove favourite')
    items_label = "Items that will be removed from your favourites list"

    def make_changes(self):
        items = self.items_to_change
        self.user.profile.favourites.remove(*items)
        return _('%(num_items)s items removed from favourites') % {'num_items': len(items)}


class ChangeStateForm(ChangeStatusForm, BulkActionForm):
    confirm_page = "aristotle_mdr/actions/bulk_actions/change_status.html"
    classes="fa-university"
    action_text = _('Change registration status')
    items_label = "These are the items that will be registered. Add or remove additional items with the autocomplete box."

    def __init__(self, *args, **kwargs):
        super(ChangeStateForm, self).__init__(*args, **kwargs)
        self.add_registration_authority_field()

    def make_changes(self):
        import reversion
        if not self.user.profile.is_registrar:
            raise PermissionDenied
        ras = self.cleaned_data['registrationAuthorities']
        state = self.cleaned_data['state']
        items = self.items_to_change
        regDate = self.cleaned_data['registrationDate']
        cascade = self.cleaned_data['cascadeRegistration']
        changeDetails = self.cleaned_data['changeDetails']
        failed = []
        success = []
        with transaction.atomic(), reversion.revisions.create_revision():
            reversion.revisions.set_user(self.user)

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
            message = _(
                "%(num_items)s items registered in %(num_ra)s registration authorities. \n"
                "Some items failed, they had the id's: %(bad_ids)s"
            ) % {
                'num_items': len(items),
                'num_ra': len(ras),
                'bad_ids': ",".join(bad_items)
            }
            reversion.revisions.set_comment(changeDetails + "\n\n" + message)
            return message

    @classmethod
    def can_use(cls, user):
        return user_is_registrar(user)


class RequestReviewForm(LoggedInBulkActionForm):
    confirm_page = "aristotle_mdr/actions/bulk_actions/request_review.html"
    classes="fa-flag"
    action_text = _('Request review')
    items_label = "These are the items that will be reviewed. Add or remove additional items with the autocomplete box."

    registration_authority=forms.ModelChoiceField(
        label="Registration Authority",
        queryset=MDR.RegistrationAuthority.objects.all(),
    )
    registration_date = forms.DateField(
        required=False,
        label=_("Registration date"),
        widget=DateTimePicker(options={"format": "YYYY-MM-DD"}),
        initial=timezone.now()
    )
    state = forms.ChoiceField(choices=MDR.STATES, widget=forms.RadioSelect)
    cascade_registration = forms.ChoiceField(
        choices=[(0, _('No')), (1, _('Yes'))],
        help_text=_("Update the registration of associated items")
    )
    message = forms.CharField(
        required=False,
        label=_("Message for the reviewing registrar"),
        widget=forms.Textarea
    )

    def __init__(self, *args, **kwargs):
        super(RequestReviewForm, self).__init__(*args, **kwargs)

    def make_changes(self):
        import reversion
        ra = self.cleaned_data['registration_authority']
        state = self.cleaned_data['state']
        items = self.items_to_change
        cascade = self.cleaned_data['cascade_registration']
        registration_date = self.cleaned_data['registration_date']
        message = self.cleaned_data['message']

        with transaction.atomic(), reversion.revisions.create_revision():
            reversion.revisions.set_user(self.user)

            review = MDR.ReviewRequest.objects.create(
                requester=self.user,
                registration_authority=ra,
                registration_date=registration_date,
                message=message,
                state=state,
                cascade_registration=cascade
            )
            failed = []
            success = []
            for item in items:
                if item.can_view(self.user):
                    success.append(item)
                else:
                    failed.append(item)

            review.concepts = success

            user_message = mark_safe(_(
                "%(num_items)s items requested for review - <a href='%(url)s'>see the review here</a>."
            ) % {
                'num_items': len(success),
                'url': reverse('aristotle:userReviewDetails', args=[review.id])
            })
            reversion.revisions.set_comment(message + "\n\n" + user_message)
            return user_message


class ChangeWorkgroupForm(BulkActionForm):
    confirm_page = "aristotle_mdr/actions/bulk_actions/change_workgroup.html"
    classes="fa-users"
    action_text = _('Change workgroup')
    items_label="These are the items that will be moved between workgroups. Add or remove additional items with the autocomplete box."

    def __init__(self, *args, **kwargs):
        super(ChangeWorkgroupForm, self).__init__(*args, **kwargs)

        wgs = [(wg.id, wg.name) for wg in self.user.profile.workgroups]
        self.fields['workgroup']=forms.ModelChoiceField(
            label="Workgroup to move items to",
            queryset=self.user.profile.workgroups
        )
        self.fields['changeDetails']=forms.CharField(
            label="Change notes (optional)",
            required=False,
            widget=forms.Textarea
        )

    def make_changes(self):
        import reversion
        from aristotle_mdr.perms import user_can_remove_from_workgroup, user_can_move_to_workgroup
        new_workgroup = self.cleaned_data['workgroup']
        changeDetails = self.cleaned_data['changeDetails']
        items = self.cleaned_data['items']

        if not user_can_move_to_workgroup(self.user, new_workgroup):
            raise PermissionDenied

        move_from_checks = {}  # Cache workgroup permissions as we check them to speed things up

        failed = []
        success = []
        with transaction.atomic(), reversion.revisions.create_revision():
            reversion.revisions.set_user(self.user)
            for item in items:
                can_move = move_from_checks.get(item.workgroup.pk, None)
                if can_move is None:
                    can_move = user_can_remove_from_workgroup(self.user, item.workgroup)
                    move_from_checks[item.workgroup.pk] = can_move

                if not can_move:
                    failed.append(item)
                else:
                    success.append(item)
                    item.workgroup = new_workgroup
                    item.save()

            failed = list(set(failed))
            success = list(set(success))
            bad_items = sorted([str(i.id) for i in failed])
            if not bad_items:
                message = _(
                    "%(num_items)s items moved into the workgroup '%(new_wg)s'. \n"
                ) % {
                    'new_wg': new_workgroup.name,
                    'num_items': len(success),
                }
            else:
                message = _(
                    "%(num_items)s items moved into the workgroup '%(new_wg)s'. \n"
                    "Some items failed, they had the id's: %(bad_ids)s"
                ) % {
                    'new_wg': new_workgroup.name,
                    'num_items': len(success),
                    'bad_ids': ",".join(bad_items)
                }
            reversion.revisions.set_comment(changeDetails + "\n\n" + message)
            return message

    @classmethod
    def can_use(cls, user):
        return user_can_move_any_workgroup(user)


class DownloadActionForm(BulkActionForm):
    def make_changes(self):
        items = self.items_to_change
        from aristotle_mdr.contrib.redirect.exceptions import Redirect
        raise Redirect(url=reverse('aristotle:bulk_download', kwargs={'download_type': self.download_type}) + ('?title=%s&' % self.title) + "&".join(['items=%s' % i.id for i in items]))


class QuickPDFDownloadForm(DownloadActionForm):
    classes="fa-file-pdf-o"
    action_text = _('Quick PDF download')
    items_label = "Items that are downloaded"
    download_type= 'pdf'
    title = None


class BulkDownloadForm(DownloadActionForm):
    confirm_page = "aristotle_mdr/actions/bulk_actions/bulk_download.html"
    classes="fa-download"
    action_text = _('Bulk download')
    items_label="These are the items that will be downloaded"

    title = forms.CharField(
        required=False,
        label=_("Title for the document"),
        # widget=forms.Textarea
    )
    download_type = forms.ChoiceField(
        choices=[(setting[0], setting[1]) for setting in getattr(settings, 'ARISTOTLE_DOWNLOADS', [])],
        widget=forms.RadioSelect
    )

    def make_changes(self):
        self.download_type = self.cleaned_data['download_type']
        self.title = self.cleaned_data['title']
        items = self.cleaned_data['items']
        super(BulkDownloadForm, self).make_changes()
