import mock
from django.db import DatabaseError
from django.test import Client
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test import override_settings
from django.test.utils import setup_test_environment
from aristotle_mdr.tests.utils import get_json_from_response

setup_test_environment()

cursor_wrapper = mock.Mock()
cursor_wrapper.side_effect = DatabaseError


class TestChaosMonkey(TestCase):
    def setUp(self):
        # Every test needs a client.
        self.client = Client()

    def test_its_all_ok(self):
        # Test with no value
        response = self.client.get(reverse('aristotle_mdr_hb:health'))
        self.assertEqual(response.status_code, 200)

    # @mock.patch('django.db.backends.util.CursorWrapper', cursor_wrapper)
    # @override_settings(DATABASES={})
    # def test_dead_database(self):
    #     response = self.client.get(reverse('aristotle_mdr_hb:health'))
    #     print response.content
    #     details = json.loads(response.content)

    #     self.assertEqual(response.status_code, 500)
    #     self.assertEqual(details['status_code'], 500)
    #     self.assertEqual(details['database']['status'], "notok")
    #     self.assertTrue("error" in details['database'].keys())

    @override_settings(CACHES={})
    def test_dead_cache(self):
        response = self.client.get(reverse('aristotle_mdr_hb:health'))
        details = get_json_from_response(response)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(details['status_code'], 500)
        self.assertEqual(details['cache']['status'], "notok")
        self.assertTrue("error" in details['cache'].keys())
