# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('aristotle_mdr_self_publish', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='publicationrecord',
            name='publication_date',
            field=models.DateField(default=django.utils.timezone.now, help_text='Enter a date in the future to specify the date is published from.'),
        ),
        migrations.AlterField(
            model_name='publicationrecord',
            name='visibility',
            field=models.IntegerField(default=0, help_text='Specify who can see this item.', choices=[(0, 'Public'), (1, 'Logged in users only'), (2, 'Make hidden')]),
        ),
    ]
