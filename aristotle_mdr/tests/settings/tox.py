import os
from aristotle_mdr.tests.settings.settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.environ.get('TOXDIR'),'test_database'),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'aristotle-mdr-cache'
    }
}

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'aristotle_mdr.contrib.search_backends.facetted_whoosh.FixedWhooshEngine',
        'PATH': os.path.join(os.path.dirname(__file__), 'whoosh_index'),
        'INCLUDE_SPELLING': True,
    },
}
