# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('extension_test', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='questionnaire',
            name='end_date',
            field=models.DateField(help_text='Date the questionnaire was run until', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='questionnaire',
            name='start_date',
            field=models.DateField(help_text='Date the questionnaire was run from', null=True, blank=True),
        ),
    ]
