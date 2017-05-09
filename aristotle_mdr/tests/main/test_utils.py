from django.test import TestCase
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.urlresolvers import reverse

import aristotle_mdr.tests.utils as utils
from aristotle_mdr import models
import datetime

from django.test.utils import setup_test_environment
setup_test_environment()


class UtilsTests(TestCase):
    def test_reverse_slugs(self):
        item = models.ObjectClass.objects.create(name=" ",definition="my definition",submitter=None)
        ra = models.RegistrationAuthority.objects.create(name=" ",definition="my definition")
        org = models.Organization.objects.create(name=" ",definition="my definition")
        wg = models.Workgroup.objects.create(name=" ",definition="my definition")
        
        from aristotle_mdr import utils
        
        self.assertTrue('--' in utils.url_slugify_concept(item))
        self.assertTrue('--' in utils.url_slugify_workgroup(wg))
        self.assertTrue('--' in utils.url_slugify_registration_authoritity(ra))
        self.assertTrue('--' in utils.url_slugify_organization(org))
