from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings, modify_settings
from django.test.utils import setup_test_environment
from django.utils import timezone

import aristotle_mdr.models as models
import aristotle_mdr.perms as perms
from aristotle_mdr.utils import url_slugify_concept
from aristotle_mdr.forms.creation_wizards import WorkgroupVerificationMixin,CheckIfModifiedMixin

setup_test_environment()
from aristotle_mdr.tests import utils
import datetime


class LoggedInViewConceptBrowsePages(utils.LoggedInViewPages):
    defaults = {}

    def setUp(self):
        super(LoggedInViewConceptBrowsePages, self).setUp()

        self.item1 = self.itemType.objects.create(name="Test Item 1 (visible to tested viewers)",definition="my definition",workgroup=self.wg1,**self.defaults)
        self.item2 = self.itemType.objects.create(name="Test Item 2 (NOT visible to tested viewers)",definition="my definition",workgroup=self.wg2,**self.defaults)
        self.item3 = self.itemType.objects.create(name="Test Item 3 (visible to tested viewers)",definition="my definition",workgroup=self.wg1,**self.defaults)

        # Item 3 and 4 need to have a shared string in their name for `test_editor_can_view_browse_with_filters`
        # So, the character `3` *must* be in the name below!
        self.item4 = self.itemType.objects.create(name="Test Item 4 also like item 3 (visible to tested viewers)",definition="my definition",workgroup=self.wg1,**self.defaults)

        self.ra.register(self.item4,self.ra.public_state,self.su)

    def test_browse_pages_load(self):
        response = self.client.get(reverse('browse_apps'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('browse_models', args=['aristotle_mdr']))
        self.assertEqual(response.status_code, 200)

    def test_anon_can_view_browse(self):
        self.logout()
        response = self.client.get(
            reverse("browse_concepts",args=[self.itemType._meta.app_label,self.itemType._meta.model_name])
            )
        self.assertEqual(response.status_code,200)
        self.assertContains(response, self.item4.name)
        self.assertNotContains(response, self.item2.name)

    def test_zero_item_should_not_show(self):
        self.logout()
        response = self.client.get(
            reverse("browse_concepts",args=[self.itemType._meta.app_label,self.itemType._meta.model_name])
            )

        self.assertEqual(response.status_code, 200)
        if(self.itemType.objects.all().count() == 0):
            self.assertNotContains(response, self.itemType._meta.model_name)
        else:
            self.assertContains(response, self.itemType._meta.model_name)

    def test_editor_can_view_browse(self):
        self.login_editor()
        response = self.client.get(
            reverse("browse_concepts",args=[self.itemType._meta.app_label,self.itemType._meta.model_name])
            )
        self.assertEqual(response.status_code,200)
        self.assertContains(response, self.item1.name)
        self.assertContains(response, self.item4.name)
        self.assertNotContains(response, self.item2.name)

    def test_editor_can_view_browse_with_filters(self):
        self.login_editor()
        response = self.client.get(
            reverse("browse_concepts",args=[self.itemType._meta.app_label,self.itemType._meta.model_name]),
            {'f':'name__icontains:3'}
            )
        self.assertEqual(response.status_code,200)
        self.assertNotContains(response, self.item1.name)
        self.assertNotContains(response, self.item2.name)
        self.assertContains(response, self.item3.name)
        self.assertContains(response, self.item4.name)

        response = self.client.get(
            reverse("browse_concepts",args=[self.itemType._meta.app_label,self.itemType._meta.model_name]),
            {'f':'a_fake_query_that_fails:3'}
            )
        self.assertEqual(response.status_code,200)
        self.assertContains(response, self.item1.name)
        self.assertNotContains(response, self.item2.name)
        self.assertContains(response, self.item3.name)
        self.assertContains(response, self.item4.name)

        response = self.client.get(
            reverse("browse_concepts",args=[self.itemType._meta.app_label,self.itemType._meta.model_name]),
            {'f':'another_fake_query_that_fails'}
            )
        self.assertEqual(response.status_code,200)
        self.assertContains(response, self.item1.name)
        self.assertNotContains(response, self.item2.name)
        self.assertContains(response, self.item3.name)
        self.assertContains(response, self.item4.name)

    def test_editor_can_view_browse_with_slot_filters(self):
        from aristotle_mdr.contrib.slots.models import Slot
        slot_name ="test"

        self.login_editor()
        response = self.client.get(
            reverse("browse_concepts",args=[self.itemType._meta.app_label,self.itemType._meta.model_name]),
            {'sf':'%s:hello'%slot_name}
            )
        self.assertEqual(response.status_code,200)
        self.assertNotContains(response, self.item1.name)
        self.assertNotContains(response, self.item2.name)
        self.assertNotContains(response, self.item3.name)
        self.assertNotContains(response, self.item4.name)

        slot = Slot.objects.create(concept=self.item1.concept, name=slot_name, value="hello")

        response = self.client.get(
            reverse("browse_concepts",args=[self.itemType._meta.app_label,self.itemType._meta.model_name]),
            {'sf':'%s:hello'%slot_name}
            )
        self.assertEqual(response.status_code,200)
        self.assertContains(response, self.item1.name)
        self.assertNotContains(response, self.item2.name)
        self.assertNotContains(response, self.item3.name)
        self.assertNotContains(response, self.item4.name)

        response = self.client.get(
            reverse("browse_concepts",args=[self.itemType._meta.app_label,self.itemType._meta.model_name]),
            {'sf':['%s:hello'%slot_name,'%s:bye'%slot_name]}
            )
        self.assertEqual(response.status_code,200)
        self.assertContains(response, self.item1.name)
        self.assertNotContains(response, self.item2.name)
        self.assertNotContains(response, self.item3.name)
        self.assertNotContains(response, self.item4.name)

        response = self.client.get(
            reverse("browse_concepts",args=[self.itemType._meta.app_label,self.itemType._meta.model_name]),
            {'sf':'another_fake_query_that_fails'}
            )
        self.assertEqual(response.status_code,200)
        self.assertContains(response, self.item1.name)
        self.assertNotContains(response, self.item2.name)
        self.assertContains(response, self.item3.name)
        self.assertContains(response, self.item4.name)

    def test_editor_can_view_browse_with_two_slot_filters(self):
        from aristotle_mdr.contrib.slots.models import Slot
        slot_name_1 = "test1"
        slot_name_2 = "test2"

        self.login_editor()
        response = self.client.get(
            reverse("browse_concepts",args=[self.itemType._meta.app_label,self.itemType._meta.model_name]),
            {'sf':'%s:hello'%slot_name_1}
            )
        self.assertEqual(response.status_code,200)
        self.assertNotContains(response, self.item1.name)
        self.assertNotContains(response, self.item3.name)

        # Make some slots
        Slot.objects.create(concept=self.item1.concept, name=slot_name_1, value="hello")
        Slot.objects.create(concept=self.item1.concept, name=slot_name_2, value="other")
        Slot.objects.create(concept=self.item3.concept, name=slot_name_1, value="hello")

        self.login_editor()
        response = self.client.get(
            reverse("browse_concepts",args=[self.itemType._meta.app_label,self.itemType._meta.model_name]),
            {'sf':'%s:hello'%slot_name_1}
            )
        self.assertEqual(response.status_code,200)
        self.assertContains(response, self.item1.name)
        self.assertContains(response, self.item3.name)

        response = self.client.get(
            reverse("browse_concepts",args=[self.itemType._meta.app_label,self.itemType._meta.model_name]),
            {'sf': [
                '%s:hello'%slot_name_1,
                '%s:other'%slot_name_2,
            ]}
            )
        self.assertEqual(response.status_code,200)
        self.assertContains(response, self.item1.name)
        self.assertNotContains(response, self.item2.name)
        self.assertNotContains(response, self.item3.name)
        self.assertNotContains(response, self.item4.name)

    def test_itemtypes_with_no_items_dont_show_up(self):
        self.login_editor()

        response = self.client.get(reverse('browse_models', args=['aristotle_mdr']))
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, self.itemType.get_verbose_name_plural())
        self.assertContains(response, 
            reverse("browse_concepts",args=[self.itemType._meta.app_label,self.itemType._meta.model_name]),
        )

        self.item1.delete() #/browse/aristotle_mdr/objectclass
        self.item3.delete()
        self.item4.delete()

        response = self.client.get(reverse('browse_models', args=['aristotle_mdr']))
        self.assertEqual(response.status_code, 200)

        self.assertNotContains(response, self.itemType.get_verbose_name_plural())
        self.assertNotContains(response, 
            reverse("browse_concepts",args=[self.itemType._meta.app_label,self.itemType._meta.model_name]),
        )


class ObjectClassViewPage(LoggedInViewConceptBrowsePages,TestCase):
    url_name='objectClass'
    itemType=models.ObjectClass
class PropertyViewPage(LoggedInViewConceptBrowsePages,TestCase):
    url_name='property'
    itemType=models.Property
class UnitOfMeasureViewPage(LoggedInViewConceptBrowsePages,TestCase):
    url_name='unitOfMeasure'
    itemType=models.UnitOfMeasure
class ValueDomainViewPage(LoggedInViewConceptBrowsePages,TestCase):
    url_name='valueDomain'
    itemType=models.ValueDomain

class ConceptualDomainViewPage(LoggedInViewConceptBrowsePages,TestCase):
    url_name='conceptualDomain'
    itemType=models.ConceptualDomain
class DataElementConceptViewPage(LoggedInViewConceptBrowsePages,TestCase):
    url_name='dataElementConcept'
    itemType=models.DataElementConcept
class DataElementViewPage(LoggedInViewConceptBrowsePages,TestCase):
    url_name='dataElement'
    itemType=models.DataElement

    def test_template_overriden(self):
        """
        see file tests/apps/extension_test/templates/aristotle_mdr_browse/aristotle_mdr/dataelement_list.html
        """
        check_text = "This is a customised browse list of data elements"
        response = self.client.get(
            reverse("browse_concepts",args=[self.itemType._meta.app_label,self.itemType._meta.model_name])
        )
        self.assertContains(response, check_text)

class DataElementDerivationViewPage(LoggedInViewConceptBrowsePages,TestCase):
    url_name='dataelementderivation'
    itemType=models.DataElementDerivation
