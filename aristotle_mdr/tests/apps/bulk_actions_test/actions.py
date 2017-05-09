from django import forms
from aristotle_mdr.forms.bulk_actions import BulkActionForm
from django.utils.translation import ugettext_lazy as _


class StaffDeleteActionForm(BulkActionForm):
    action_text = _('Delete')
    classes="fa-trash"
    confirm_page = "confirm_delete.html"
    items_label="Items to delete",

    safe_to_delete = forms.BooleanField(required=True, label="Tick to confirm deletion")

    @classmethod
    def can_use(cls, user):
        return user.is_staff

    def make_changes(self):
        if not self.user.is_staff:
            raise PermissionDenied
        else:
            self.cleaned_data['items'].delete()
        return "Items deleted"


# Incomplete test bulk actions
class IncompleteActionForm(BulkActionForm):
    def make_changes(self):
        pass
