from django.test import TestCase

import aristotle_mdr.models as models
import aristotle_mdr.perms as perms
import aristotle_mdr.tests.utils as utils
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.template import TemplateSyntaxError

from django.test.utils import setup_test_environment
setup_test_environment()


class TextDownloader(utils.LoggedInViewPages, TestCase):
    def test_logged_in_user_text_downloads(self):
        self.login_editor()
        oc = models.ObjectClass.objects.create(name="OC1", workgroup=self.wg1)
        de = models.DataElement.objects.create(name="DE1", definition="A test data element", workgroup=self.wg1)
        dec = models.DataElementConcept.objects.create(name="DEC", workgroup=self.wg1)
        de2 = models.DataElement.objects.create(name="DE2", workgroup=self.wg2)

        response = self.client.get(reverse('aristotle:download', args=['txt', oc.id]))
        # This template does not exist on purpose and will throw an error
        self.assertEqual(response.status_code, 404)

        response = self.client.get(reverse('aristotle:download', args=['txt', de.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, de.name)
        self.assertContains(response, de.definition)

        response = self.client.get(reverse('aristotle:download', args=['txt', de2.id]))
        # This item is not visible to the logged in user and will throw an error
        self.assertEqual(response.status_code, 403)

        with self.assertRaises(TemplateSyntaxError):
            # This template is broken on purpose and will throw an error
            response = self.client.get(reverse('aristotle:download', args=['txt', dec.id]))
