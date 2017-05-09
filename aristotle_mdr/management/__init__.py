from django.db.models import signals
from django.contrib.auth.models import User
import aristotle_mdr
import sys
from django.conf import settings


def loadSystemData(**kwargs):
    # Always load system data when running commands, just to make sure everything is there.
    from django.core.management import call_command
    call_command('loaddata', 'system.json')

signals.post_migrate.connect(loadSystemData, sender=aristotle_mdr.models)
