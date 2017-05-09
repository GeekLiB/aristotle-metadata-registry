# -*- coding: utf-8 -*-
import os
# from aristotle_mdr.contrib.channels.settings import CHANNEL_LAYERS, HAYSTACK_SIGNAL_PROCESSOR

BASE_DIR = os.getenv('aristotlemdr__BASE_DIR', os.path.dirname(os.path.dirname(__file__)))
SECRET_KEY = os.getenv('aristotlemdr__SECRET_KEY', "OVERRIDE_THIS_IN_PRODUCTION")
STATIC_ROOT = os.getenv('aristotlemdr__STATIC_ROOT', os.path.join(BASE_DIR, "static"))
MEDIA_ROOT = os.getenv('aristotlemdr__MEDIA_ROOT', os.path.join(BASE_DIR, "media"))

TEMPLATES_DIRS = [os.path.join(BASE_DIR, 'templates')]
FIXTURES_DIRS = [os.path.join(BASE_DIR, 'fixtures')]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# https://docs.djangoproject.com/en/1.6/ref/settings/#databases
# This provides for quick easy set up, but should be changed to a production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'pos.db3'),
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'aristotle-mdr-cache'
    }
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': TEMPLATES_DIRS,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.request',
                'django.template.context_processors.static',
                'aristotle_mdr.context_processors.settings',
                'django.contrib.messages.context_processors.messages',
            ],
            'debug': DEBUG
        },
    },
]

MEDIA_URL = '/media/'
CKEDITOR_UPLOAD_PATH = 'uploads/'


# Required for admindocs, see: https://code.djangoproject.com/ticket/21386
SITE_ID=None

# This gets called because of the DataElementConcept.property attribute.
# Not sure how to resolve this one yet.
SILENCED_SYSTEM_CHECKS = ['models.E006']

ALLOWED_HOSTS = []

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

INSTALLED_APPS = (
    'aristotle_mdr',
    'aristotle_mdr.contrib.generic',
    'aristotle_mdr.contrib.help',
    'aristotle_mdr.contrib.slots',
    'aristotle_mdr.contrib.identifiers',
    'aristotle_mdr.contrib.browse',

    'channels',
    'haystack_channels',

    'dal',
    'dal_select2',

    'haystack',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'ckeditor',
    'ckeditor_uploader',

    'static_precompiler',
    'bootstrap3',
    'bootstrap3_datetime',
    'reversion',  # https://github.com/etianen/django-reversion
    'reversion_compare',  # https://github.com/jedie/django-reversion-compare

    'notifications',
)

USE_L10N = True
USE_TZ = True
USE_I18N = True

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'aristotle_mdr.contrib.redirect.middleware.RedirectMiddleware',


    # 'reversion.middleware.RevisionMiddleware',
)


ROOT_URLCONF = 'aristotle_mdr.urls'
LOGIN_REDIRECT_URL = '/account/home'
LOGIN_URL = '/login'
LOGOUT_URL = '/logout'

STATIC_URL = '/static/'
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'static_precompiler.finders.StaticPrecompilerFinder',
)
ADMIN_MEDIA_PREFIX = '/static/admin/'

if DEBUG:
    STATIC_PRECOMPILER_CACHE_TIMEOUT = 1
    STATIC_PRECOMPILER_DISABLE_AUTO_COMPILE = False

BOOTSTRAP3 = {
    # The Bootstrap base URL
    'base_url': '/static/aristotle_mdr/bootstrap/',
}

ADD_REVERSION_ADMIN = True

# We need this to make sure users can see all extensions.
AUTHENTICATION_BACKENDS = ('aristotle_mdr.backends.AristotleBackend',)

ARISTOTLE_SETTINGS = {
    'SEPARATORS': {
        'DataElement': ', ',
        'DataElementConcept': u'–'
    },
    'SITE_NAME': 'Default Site Name',  # 'The main title for the site.'
    'SITE_BRAND': '/static/aristotle_mdr/images/aristotle_small.png',  # URL for the Site-wide logo
    'SITE_INTRO': 'Use Default Site Name to search for metadata...',  # 'Intro text use on the home page as a prompt for users.'
    'SITE_DESCRIPTION': 'About this site',  # 'The main title for the site.'
    'CONTENT_EXTENSIONS': [],
    'PDF_PAGE_SIZE': 'A4',
    'WORKGROUP_CHANGES': [],  # ['admin'] # or manager or submitter,
    'BULK_ACTIONS': {
        'add_favourites': 'aristotle_mdr.forms.bulk_actions.AddFavouriteForm',
        'remove_favourites': 'aristotle_mdr.forms.bulk_actions.RemoveFavouriteForm',
        'change_state': 'aristotle_mdr.forms.bulk_actions.ChangeStateForm',
        'move_workgroup': 'aristotle_mdr.forms.bulk_actions.ChangeWorkgroupForm',
        'request_review': 'aristotle_mdr.forms.bulk_actions.RequestReviewForm',
        'bulk_download': 'aristotle_mdr.forms.bulk_actions.BulkDownloadForm',
    },
    'DASHBOARD_ADDONS': [],
    'METADATA_CREATION_WIZARDS': [
        {
            'app_label': 'aristotle_mdr',
            'model': 'DataElement',
            'class': 'aristotle_mdr.views.wizards.DataElementWizard',
            'link': 'create/wizard/aristotle_mdr/dataelement',
        },
        {
            'app_label': 'aristotle_mdr',
            'model': 'DataElementConcept',
            'class': 'aristotle_mdr.views.wizards.DataElementConceptWizard',
            'link': 'create/wizard/aristotle_mdr/dataelementconcept',
        }
    ]
}
ARISTOTLE_DOWNLOADS = [
    # (fileType, menu, font-awesome-icon, module)
    ('pdf', 'PDF', 'fa-file-pdf-o', 'aristotle_mdr', 'Downloads for various content types in the PDF format'),
    ('csv-vd', 'CSV list of values', 'fa-file-excel-o', 'aristotle_mdr', 'CSV downloads for value domain codelists'),
]

CKEDITOR_CONFIGS = {
    'default': {
        # 'toolbar': 'full',
        'toolbar': [
            {'name': 'clipboard', 'items': ['Cut', 'Copy', 'Paste', 'PasteText', '-', 'Undo', 'Redo']},
            {'name': 'basicstyles', 'items': ['Bold', 'Italic', 'Subscript', 'Superscript', '-', 'RemoveFormat']},
            {'name': 'links', 'items': ['Link', 'Unlink']},
            {'name': 'paragraph', 'items': ['NumberedList', 'BulletedList', '-', 'Blockquote']},
            {'name': 'insert', 'items': ['Image', 'Table', 'HorizontalRule', 'SpecialChar']},
            {'name': 'document', 'items': ['Maximize', 'Source']},
        ],
        'width': "",
    },
}

HAYSTACK_SIGNAL_PROCESSOR = 'aristotle_mdr.contrib.help.signals.AristotleHelpSignalProcessor'
# HAYSTACK_SEARCH_RESULTS_PER_PAGE = 10
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'aristotle_mdr.contrib.search_backends.facetted_whoosh.FixedWhooshEngine',
        'PATH': os.path.join(os.path.dirname(__file__), 'whoosh_index'),
        'INCLUDE_SPELLING': True,
    },
}

STATIC_PRECOMPILER_COMPILERS = (
    ('static_precompiler.compilers.LESS', {"executable": "lesscpy"}),
)
