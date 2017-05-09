"""
Django settings for example_mdr project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/

# Quick-start development settings - unsuitable for production
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

# Import all of the necessary settings to get the Aristotle server working.
# These are defaults and can be overridden within this file.
from aristotle_mdr.required_settings import *

# Override these
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TEMPLATE_DIRS = [os.path.join(BASE_DIR, 'templates')]
FIXTURES_DIRS = [os.path.join(BASE_DIR, 'fixtures')]
STATIC_ROOT =os.path.join(BASE_DIR, "static")

# If you are using the Aristotle Glossary, uncomment the command below to enable
# the glossary insertion button in the rich text editor
#!aristotle_glossary!from aristotle_glossary.settings import CKEDITOR_CONFIGS

# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/
# SECURITY WARNING: keep the secret key used in production secret!
# You need to
SECRET_KEY = 'Change-this-key-as-soon-as-you-can'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition
# Below is a barebones "INSTALLED_APPS" configuration for Aristotle.
# Some extra apps are included, but commented out, to demonstrate how to add additional apps.
# To install these uncomment the lines for the apps you want in the following locations:
# * INSTALLED_APPS setting in this file (just below)
# * CONTENT_EXTENSIONS setting in this file in ARISTOTLE_SETTINGS
# * the installation command in `requirements.txt` file
# * the url import in `example_mdr/urls.py`
INSTALLED_APPS = (
    #!aristotle_ddi_utils! 'aristotle_ddi_utils', # Download formats in the DDI3.2 XML format - https://github.com/aristotle-mdr/aristotle-ddi-utils
    #!aristotle_dse! 'aristotle_dse', # Additional models for describing datasets - https://github.com/aristotle-mdr/aristotle-dataset-extensions
    #!aristotle_glossary! 'aristotle_glossary', # Model for managing and inserting glossary content - https://github.com/aristotle-mdr/aristotle-glossary
    #!aristotle_mdr_api! 'aristotle_mdr_api', # JSON API for programmatic access to content
    #!aristotle_mdr_api! 'rest_framework', # Needed for the above
) + INSTALLED_APPS # Installs the required apps to run aristotle.

ROOT_URLCONF = 'example_mdr.urls'

WSGI_APPLICATION = 'example_mdr.wsgi.application'


# Database
# Below is the default database setup, which uses the file-based SQLite database.
# For production systems, examine the django guide below to getting other databases configured.
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'
MEDIA_ROOT = os.path.join(BASE_DIR,'/media/')
MEDIA_URL = '/media/'
# This is a sub-directory under the MEDIA_ROOT where uploads from CKEDITOR are placed.
CKEDITOR_UPLOAD_PATH = 'uploads/'

#Aristotle settings are below, settings these gives the ability to personalise this particular installation.

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': os.path.join(os.path.dirname(__file__), 'whoosh_index'),
        'INCLUDE_SPELLING':True,
    },
}
ARISTOTLE_SETTINGS.update({
    'SITE_NAME': 'Aristotle-MDR Demo Server', # 'The main title for the site.'
    'SITE_BRAND': '/static/aristotle_mdr/images/aristotle_small.png', # URL for the Site-wide logo
    'SITE_INTRO': 'Use Default Site Name to search for metadata...', # 'Intro text use on the home page as a prompt for users.'
    'SITE_DESCRIPTION': 'About this site', # 'The main title for the site.'
    'CONTENT_EXTENSIONS' : [ #Extensions that add additional object types for search/display.
            #!aristotle_dse! 'aristotle_dse',
            #!aristotle_glossary! 'aristotle_glossary',
        ]
    })
# Specified the agency to use when outputing items in the DDI XML format.
#!aristotle_ddi_utils!ARISTOTLE_DDI_AGENCY = "demo.ddi.aristotle_mdr"

# This option gives a site the ability to register the different download options available for the site
# This invoked in templates using the aristotle template tag "downloadMenu"
ARISTOTLE_DOWNLOADS = ARISTOTLE_DOWNLOADS + [
##!aristotle_ddi_utils!    ('ddi3.2','DDI 3.2','fa-file-code-o','aristotle_ddi_utils'),
    ]

#
GRAPPELLI_ADMIN_TITLE = "Comet admin interface"
