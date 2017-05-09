# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
from django.conf import settings
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('aristotle_mdr', '0012_better_workflows'),
    ]

    operations = [
        migrations.CreateModel(
            name='PublicationRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('visibility', models.IntegerField(default=0, help_text='Status of a review', choices=[(0, 'Public'), (1, 'Logged in users only'), (2, 'Unpublish')])),
                ('publication_date', models.DateField(default=django.utils.timezone.now)),
                ('note', models.TextField(null=True, blank=True)),
                ('concept', models.OneToOneField(related_name='publicationrecord', to='aristotle_mdr._concept')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
