from django.test import TestCase

import aristotle_mdr.tests.utils as utils
from aristotle_mdr.models import ObjectClass, Workgroup
from django.core.urlresolvers import reverse

from aristotle_mdr.tests.main.test_bulk_actions import BulkActionsTest

from django.test.utils import setup_test_environment
setup_test_environment()


class TestBulkActions(BulkActionsTest, TestCase):
    def setUp(self):
        super(TestBulkActions, self).setUp()
        self.item = ObjectClass.objects.create(
            name="Test Object",
            workgroup=self.wg1,
        )
        self.su.profile.favourites.add(self.item)

    def test_incomplete_action_exists(self):
        self.login_superuser()
        response = self.client.get(reverse('aristotle:userFavourites'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'incomplete action')

class TestDeleteBulkAction(BulkActionsTest, TestCase):

    def test_delete_by_superuser(self):
        self.login_superuser()

        self.assertTrue(self.su.is_staff)

        num_items = ObjectClass.objects.count()
        response = self.client.post(
            reverse('aristotle:bulk_action'),
            {
                'bulkaction': 'delete',
                'safe_to_delete': True,
                'items': [self.item1.id, self.item2.id],
            }
        )
        self.assertContains(response, 'Use this page to confirm you wish to delete the following items')

        response = self.client.post(
            reverse('aristotle:bulk_action'),
            {
                'bulkaction': 'delete',
                'safe_to_delete': True,
                'items': [self.item1.id, self.item2.id],
                "confirmed": True
            }
        )
        self.assertEqual(num_items - 2, ObjectClass.objects.count())

    def test_delete_by_editor(self):
        
        self.editor.is_staff = False
        self.editor.save()
        self.editor = self.editor.__class__.objects.get(pk=self.editor.pk)  # decache
        self.assertFalse(self.editor.is_staff)
        self.login_editor()

        num_items = ObjectClass.objects.count()
        response = self.client.post(
            reverse('aristotle:bulk_action'),
            {
                'bulkaction': 'delete',
                'safe_to_delete': True,
                'items': [self.item1.id, self.item2.id],
            },
            follow=True
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.post(
            reverse('aristotle:bulk_action'),
            {
                'bulkaction': 'delete',
                'safe_to_delete': True,
                'items': [self.item1.id, self.item2.id],
                "confirmed": True
            }
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(num_items, ObjectClass.objects.count())
