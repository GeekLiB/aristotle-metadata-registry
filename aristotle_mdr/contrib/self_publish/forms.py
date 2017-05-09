from django.forms import ValidationError, ModelForm
from aristotle_mdr.contrib.self_publish.models import PublicationRecord
from bootstrap3_datetime.widgets import DateTimePicker
from django.forms import RadioSelect


class MetadataPublishForm(ModelForm):
    class Meta:
        model = PublicationRecord
        exclude = ('user', 'concept')
        widgets = {
            'publication_date': DateTimePicker(options={"format": "YYYY-MM-DD"}),
            'visibility': RadioSelect()
        }
