from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings, modify_settings
from django.test.utils import setup_test_environment

from aristotle_mdr.contrib.slots import models
from aristotle_mdr.models import ObjectClass, Workgroup
from aristotle_mdr.tests import utils
from aristotle_mdr.tests.main.test_bulk_actions import BulkActionsTest

setup_test_environment()


class TestSlotsPagesLoad(utils.LoggedInViewPages, TestCase):
    def test_similar_slots_page(self):

        slot_name = 'my_slot_name'
        slot_type = ''

        # Will be glad to not have so many cluttering workgroups everywhere!
        wg = Workgroup.objects.create(name='test wg')
        oc1 = ObjectClass.objects.create(
            name="test obj1",
            definition="test",
            workgroup=wg
        )
        oc2 = ObjectClass.objects.create(
            name="test  obj2",
            definition="test",
            workgroup=wg
        )
        models.Slot.objects.create(concept=oc1.concept, name=slot_name, type=slot_type, value=1)
        models.Slot.objects.create(concept=oc2.concept, name=slot_name, type=slot_type, value=2)

        self.login_superuser()
        # Test with no value
        response = self.client.get(reverse('aristotle_slots:similar_slots', kwargs={'slot_name': slot_name}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, oc1.name)
        self.assertContains(response, oc2.name)

        # Test with value is 1
        response = self.client.get(
            reverse('aristotle_slots:similar_slots', kwargs={'slot_name': slot_name}),
            {'value': 1}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, oc1.name)
        self.assertNotContains(response, oc2.name)

        self.logout()
        # Test with no value
        response = self.client.get(reverse('aristotle_slots:similar_slots', kwargs={'slot_name': slot_name}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, oc1.name)
        self.assertNotContains(response, oc2.name)

    def test_long_slots(self):
        oc1 = ObjectClass.objects.create(
            name="test obj1",
            definition="test",
        )

        slot = models.Slot.objects.create(concept=oc1.concept, name="long slot", value="a" * 512)
        slot = models.Slot.objects.get(pk=slot.pk)
        self.assertTrue(slot.value=="a" * 512)
        self.assertTrue(len(slot.value) > 256)


class TestSlotsBulkAction(BulkActionsTest, TestCase):
    def setUp(self, *args, **kwargs):
        super(TestSlotsBulkAction, self).setUp(*args, **kwargs)
        self.item5 = ObjectClass.objects.create(name="OC5", definition="OC5 definition", workgroup=self.wg2)
        self.slot_name = 'my_name'
        self.slot_type = 'bulk_insert'

    def test_bulk_set_slot_on_permitted_items(self):
        self.login_editor()

        self.assertEqual(self.editor.profile.favourites.count(), 0)
        test_value = 'Insert Tab A into Slot B'
        response = self.client.post(
            reverse('aristotle:bulk_action'),
            {
                'bulkaction': 'add_slots',
                'items': [self.item1.id, self.item2.id],
                'slot_name': self.slot_name,
                'slot_type': self.slot_type,
                'value': test_value,
                "confirmed": True
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(2, len(models.concepts_with_similar_slots(user=self.editor, name=self.slot_name, value=test_value)))
        self.assertEqual(2, len(models.concepts_with_similar_slots(user=self.editor, _type=self.slot_type, value=test_value)))

    def test_bulk_set_slot_on_forbidden_items(self):
        self.login_editor()

        self.assertEqual(self.editor.profile.favourites.count(), 0)
        test_value = 'Insert Tab A into Slot B'
        response = self.client.post(
            reverse('aristotle:bulk_action'),
            {
                'bulkaction': 'add_slots',
                'items': [self.item1.id, self.item4.id, self.item5.id],
                'slot_name': self.slot_name,
                'slot_type': self.slot_type,
                'value': test_value,
                "confirmed": True
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(1, len(models.concepts_with_similar_slots(user=self.editor, name=self.slot_name, value=test_value)))
        self.assertEqual(1, len(models.concepts_with_similar_slots(user=self.editor, _type=self.slot_type, value=test_value)))
