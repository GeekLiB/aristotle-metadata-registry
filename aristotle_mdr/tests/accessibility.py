from __future__ import print_function
import os
import sys
import tempfile
from django.test import TestCase, override_settings
from django.core.management import call_command
from django.core.urlresolvers import reverse

import aristotle_mdr.models as models
import aristotle_mdr.perms as perms
import aristotle_mdr.tests.utils as utils
from wcag_zoo.validators import parade

import subprocess
import pprint

from django.test.utils import setup_test_environment
setup_test_environment()

TMP_STATICPATH = tempfile.mkdtemp(suffix='static')
STATICPATH = TMP_STATICPATH+'/static'
if not os.path.exists(STATICPATH):
    os.makedirs(STATICPATH)

MEDIA_TYPES = [
    [],
    #['(max-device-width: 480px)'],
    ['(max-width: 599px)'],
    ['(min-width: 600px)'],
    # ['(min-width: 992px)'],
    # ['(min-width: 1200px)'],
]

class TestWebPageAccessibilityBase(utils.LoggedInViewPages):

    @classmethod
    @override_settings(STATIC_ROOT = STATICPATH)
    def setUpClass(self):
        super(TestWebPageAccessibilityBase, self).setUpClass()
        self.ra = models.RegistrationAuthority.objects.create(name="Test RA")
        self.wg = models.Workgroup.objects.create(name="Test WG 1")
        self.oc = models.ObjectClass.objects.create(name="Test OC 1")
        self.pr = models.Property.objects.create(name="Test Property 1")
        self.dec = models.DataElementConcept.objects.create(name="Test DEC 1", objectClass=self.oc, property=self.pr)
        self.vd = models.ValueDomain.objects.create(name="Test DE 1")
        self.de = models.DataElement.objects.create(name="Test VD 1", dataElementConcept=self.dec, valueDomain=self.vd)

        call_command('collectstatic', interactive=False, verbosity=0)
        
        process = subprocess.Popen(
            ["ls", STATICPATH],
            stdout=subprocess.PIPE
        )
        dir_listing = process.communicate()[0].decode('utf-8')
        # Verify the static files are in the right place.
        # self.assertTrue('admin' in dir_listing)
        # self.assertTrue('aristotle_mdr' in dir_listing)
        print("All setup")

    @classmethod
    def tearDownClass(cls):
        
        # Maximum effort!
        process = subprocess.Popen(
            ["rm", TMP_STATICPATH, '-rf'],
            stdout=subprocess.PIPE
        )
        super(TestWebPageAccessibilityBase, cls).tearDownClass()

    def pages_tester(self, pages, media_types=MEDIA_TYPES):
        self.login_superuser()
        failures = 0
        for url in pages:
            print()
            print("Testing url for WCAG compliance [%s] " % url, end="", flush=True, file=sys.stderr)
            print('*', end="", flush=True, file=sys.stderr)
            for media in media_types:
                response = self.client.get(url, follow=True)
                self.assertTrue(response.status_code == 200)
                html = response.content

                results = parade.Parade(
                    level='AA', staticpath=TMP_STATICPATH,
                    skip_these_classes=['sr-only'],
                    media_types = media
                ).validate_document(html)
                if len(results['failures']) != 0:  # NOQA - This shouldn't ever happen, so no coverage needed
                    pp = pprint.PrettyPrinter(indent=4)
                    pp.pprint("Failures for '%s' with media rules [%s]" % (url, media))
                    pp.pprint(results['failures'])
                    pp.pprint(results['warnings'])
                    print("%s failures!!" % len(results['failures']) )
                else:
                    print('+', end="", flush=True, file=sys.stderr)

        self.assertTrue(len(results['failures']) == 0)            


class TestStaticPageAccessibility(TestWebPageAccessibilityBase, TestCase):
    def test_static_pages(self):
        from aristotle_mdr.urls.aristotle import urlpatterns
        pages = [
            reverse("aristotle:%s" % u.name) for u in urlpatterns
            if hasattr(u, 'name') and u.name is not None and u.regex.groups == 0
        ]
        

        self.pages_tester(pages)

class TestMetadataItemPageAccessibility(TestWebPageAccessibilityBase, TestCase):
    def test_metadata_object_pages(self):
        self.login_superuser()

        pages = [
            item.get_absolute_url() for item in [
                self.oc,
                self.pr,
                self.dec,
                self.vd,
                self.de
            ]
        ]
        self.pages_tester(pages)

class TestMetadataActionPageAccessibility(TestWebPageAccessibilityBase, TestCase):
    def test_metadata_object_action_pages(self):
        self.login_superuser()

        items = [
                self.oc,
                self.pr,
                self.dec,
                self.vd,
                self.de
        ]
        
        pages = [
            url
            for item in items
            for url in [
                reverse("aristotle:supersede", args=[item.id]),
                reverse("aristotle:deprecate", args=[item.id]),
                reverse("aristotle:edit_item", args=[item.id]),
                reverse("aristotle:clone_item", args=[item.id]),
                reverse("aristotle:item_history", args=[item.id]),
                reverse("aristotle:registrationHistory", args=[item.id]),
                reverse("aristotle:check_cascaded_states", args=[item.id]),
                # reverse("aristotle:item_history", args=[item.id]),
                # reverse("aristotle:item_history", args=[item.id]),
            ]
            if self.client.get(url, follow=True).status_code == 200
        ]
        # We skip those pages that don't exist (like object class 'child metadata' pages)

        self.pages_tester(pages, media_types = [[], ['(min-width: 600px)']])
