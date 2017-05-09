from django import forms
import aristotle_mdr.models as MDR
from aristotle_mdr.perms import user_can_view
from aristotle_mdr.contrib.autocomplete import widgets


class NewPostForm(forms.ModelForm):
    relatedItems = forms.ModelMultipleChoiceField(
        queryset=MDR._concept.objects.all(),
        label="Related items", required=False,
        widget=widgets.ConceptAutocompleteSelectMultiple()
    )

    class Meta:
        model = MDR.DiscussionPost
        fields = ['title', 'body', 'workgroup', 'relatedItems']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(NewPostForm, self).__init__(*args, **kwargs)
        self.fields['workgroup'].queryset = self.user.profile.myWorkgroups

    def clean_relatedItems(self):
        """
        Attempting to add items you don't have permission to will silently fail.
        Its unlikely to happen in normal use.
        """
        relatedItems = self.cleaned_data['relatedItems']
        relatedItems = [i for i in relatedItems if user_can_view(self.user, i)]
        return relatedItems


class EditPostForm(forms.ModelForm):
    relatedItems = forms.ModelMultipleChoiceField(
        queryset=MDR._concept.objects.all(),
        label="Related items", required=False,
        widget=widgets.ConceptAutocompleteSelectMultiple()
    )

    class Meta:
        model = MDR.DiscussionPost
        exclude = ['author', 'workgroup', 'closed']


class CommentForm(forms.ModelForm):
    class Meta:
        model = MDR.DiscussionComment
        exclude = ['author', 'post']
