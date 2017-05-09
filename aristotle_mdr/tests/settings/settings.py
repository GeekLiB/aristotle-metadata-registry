import os
import sys
from aristotle_mdr.required_settings import *

BASE = os.path.join(os.path.dirname(os.path.dirname(__file__)),'..')

sys.path.insert(1, BASE)
sys.path.insert(1, os.path.join(BASE, "tests"))
sys.path.insert(1, os.path.join(BASE, "tests/apps"))

TEMPLATES[0]['DIRS'] = [
    os.path.join(BASE, 'tests/apps/bulk_actions_test/templates')
]

SECRET_KEY = 'inara+vtkprm7@0(fsc$+grbz9-s+tmo9d)e#k(9uf8m281&$7xhdkjr'

MEDIA_ROOT = os.path.join(BASE, "media")
MEDIA_URL = '/media/'
CKEDITOR_UPLOAD_PATH = 'uploads/'

ci_runner = ""
if 'TRAVIS' in os.environ:
    ci_runner = "Travis-CI"
elif 'APPVEYOR' in os.environ:
    ci_runner = "Appveyor"
else:
    ci_runner = "Tox"

skip_migrations = (
    "ARISTOTLE_DEV_SKIP_MIGRATIONS" in os.environ or
    os.environ.get('DB') in ['mssql']
)

if os.environ.get('DB') == 'sqlite':
    print("Running %s test-suite with SQLite" % ci_runner)
    from aristotle_mdr.tests.settings.templates.db.sqlite import DATABASES
elif os.environ.get('DB') == 'postgres':
    print("Running %s test-suite with POSTGRESQL" % ci_runner)
    from aristotle_mdr.tests.settings.templates.db.postgres import DATABASES
elif os.environ.get('DB') == 'mariadb':
    print("Running %s test-suite with MariaDB" % ci_runner)
    skip_migrations = True
    from aristotle_mdr.tests.settings.templates.db.mariadb import DATABASES
elif os.environ.get('DB') == 'mssql':
    print("Running %s test-suite with MSSQL" % ci_runner)
    skip_migrations = True  # Sadly, this may not be possible until after migration 0018
    from aristotle_mdr.tests.settings.templates.db.mssql import DATABASES
elif os.environ.get('TOXDIR'):
    print("Running %s test-suite with tox SQLite" % ci_runner)
    from aristotle_mdr.tests.settings.tox import DATABASES

if os.environ.get('SEARCH') == 'whoosh':
    print("Running %s test-suite with whoosh" % ci_runner)
    if os.environ.get('VARIANT') == 'haystack':
        print("Vanilla haystack variant")
        from aristotle_mdr.tests.settings.templates.search.haystack_whoosh import HAYSTACK_CONNECTIONS
    else:
        print("Aristotle specific variant")
        from aristotle_mdr.tests.settings.templates.search.whoosh import HAYSTACK_CONNECTIONS
elif os.environ.get('SEARCH') == 'elastic':
    print("Running %s test-suite with elasticsearch" % ci_runner)
    if os.environ.get('VARIANT') == 'haystack':
        print("Vanilla haystack variant")
        from aristotle_mdr.tests.settings.templates.search.haystack_elasticsearch import HAYSTACK_CONNECTIONS
    else:
        print("Aristotle specific variant")
        from aristotle_mdr.tests.settings.templates.search.elasticsearch import HAYSTACK_CONNECTIONS
elif os.environ.get('TOXDIR'):
    print("Running  %s test-suite with whoosh" % ci_runner)
    from aristotle_mdr.tests.settings.tox import HAYSTACK_CONNECTIONS
else:
    print("Running %s test-suite with whoosh" % ci_runner)
    print("Aristotle specific variant")
    from aristotle_mdr.tests.settings.templates.search.whoosh import HAYSTACK_CONNECTIONS

if skip_migrations:  # pragma: no cover
    print("Skipping migrations")
    class DisableMigrations(object):
    
        def __contains__(self, item):
            return True
    
        def __getitem__(self, item):
            return "notmigrations"
    
    MIGRATION_MODULES = DisableMigrations()


INSTALLED_APPS = (
    # The good stuff
    'aristotle_mdr.contrib.self_publish',
    'aristotle_mdr.contrib.links',
    'templatetags',
    'extension_test',
    'text_download_test',
) + INSTALLED_APPS


# https://docs.djangoproject.com/en/1.10/topics/testing/overview/#speeding-up-the-tests
# We do a lot of user log in testing, this should speed stuff up.
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

ARISTOTLE_SETTINGS['SEPARATORS']['DataElementConcept'] = '--'
ARISTOTLE_SETTINGS['CONTENT_EXTENSIONS'] = ARISTOTLE_SETTINGS['CONTENT_EXTENSIONS'] + ['extension_test', 'aristotle_mdr_links']
ARISTOTLE_DOWNLOADS = ARISTOTLE_DOWNLOADS + [
    ('txt', 'Text', 'fa-file-pdf-o', 'text_download_test'),
]
ARISTOTLE_SETTINGS['BULK_ACTIONS'].update({
    'quick_pdf_download':'aristotle_mdr.forms.bulk_actions.QuickPDFDownloadForm',
    'delete': 'bulk_actions_test.actions.StaffDeleteActionForm',
    'incomplete': 'bulk_actions_test.actions.IncompleteActionForm',
    'add_slots': 'aristotle_mdr.contrib.slots.forms.BulkAssignSlotsForm',
})
ROOT_URLCONF = 'extension_test.urls'

# disable
__LOGGING__ = {
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console-simple': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
            },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
            },
        },
    'loggers': {
        'aristotle_mdr': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
            },
        'django': {
            'handlers': ['console-simple'],
            'level': 'INFO',
            'propagate': True,
            },
        }
    }
