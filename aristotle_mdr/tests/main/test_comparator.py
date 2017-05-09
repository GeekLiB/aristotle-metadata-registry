from django.test import TestCase

import aristotle_mdr.models as models
import aristotle_mdr.perms as perms
import aristotle_mdr.tests.utils as utils
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

import datetime
from django.utils import timezone

from reversion import revisions as reversion

from django.test.utils import setup_test_environment
setup_test_environment()


class ComparatorTester(utils.LoggedInViewPages):

    def setUp(self):
        super(ComparatorTester, self).setUp()
        self.ra = models.RegistrationAuthority.objects.create(name="Test RA")
        self.wg = models.Workgroup.objects.create(name="Setup WG")
        self.item1 = self.itemType.objects.create(name="Item with a name", workgroup=self.wg)
        self.item2 = self.itemType.objects.create(name="Item wit a different name", workgroup=self.wg)

    def test_compare_page_loads(self):
        self.logout()
        item1 = self.item1
        item2 = self.item2
        response = self.client.get(
            reverse('aristotle:compare_concepts') + "?item_a=%s&item_b=%s" % (item1.id, item2.id)
        )
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertTrue('Select a valid choice', form.errors['item_a'][0])
        self.assertTrue('Select a valid choice', form.errors['item_b'][0])
        # register items so they are now visible
        s = models.Status.objects.create(
            concept=item1,
            registrationAuthority=self.ra,
            registrationDate=timezone.now(),
            state=self.ra.public_state
        )

        response = self.client.get(
            reverse('aristotle:compare_concepts') + "?item_a=%s&item_b=%s" % (item1.id, item2.id)
        )
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertTrue('Select a valid choice', form.errors['item_b'][0])
        self.assertTrue('item_a' not in form.errors.keys())  # No error will show as we need two choices

        s = models.Status.objects.create(
            concept=item2,
            registrationAuthority=self.ra,
            registrationDate=timezone.now(),
            state=self.ra.public_state
        )
        item1 = self.itemType.objects.get(pk=item1.pk)  # decache
        item2 = self.itemType.objects.get(pk=item2.pk)  # decache

        self.assertTrue(item1.is_public())
        self.assertTrue(item2.is_public())
        response = self.client.get(
            reverse('aristotle:compare_concepts') + "?item_a=%s&item_b=%s" % (item1.id, item2.id)
        )
        self.assertEqual(response.status_code, 200)
        form = response.context['form']

        self.assertTrue('This item has no revisions', form.errors['item_a'][0])
        self.assertTrue('This item has no revisions', form.errors['item_b'][0])

        with reversion.create_revision():
            item1.definition = "bump to make a reversion"
            item1.save()
        with reversion.create_revision():
            item2.definition = "bump to make a reversion"
            item2.save()

        response = self.client.get(
            reverse('aristotle:compare_concepts') + "?item_a=%s&item_b=%s" % (item1.id, item2.id)
        )
        self.assertEqual(response.status_code, 200)
        form = response.context['form']

        self.assertTrue('item_a' not in form.errors.keys())
        self.assertTrue('item_b' not in form.errors.keys())
        self.assertContains(response, '>different </ins')  # check that we have made a diff

        same = response.context['same']
        self.assertTrue('definition' in same.keys())  # check that we have made a diff
        self.assertTrue('bump to make a reversion' in same['definition']['value'])  # check that we have made a diff


class ObjectClassComparatorTester(ComparatorTester, TestCase):
    itemType=models.ObjectClass


class ValueDomainComparatorTester(ComparatorTester, TestCase):
    itemType=models.ValueDomain

    def setUp(self):
        super(ValueDomainComparatorTester, self).setUp()

        for i in range(4):
            models.PermissibleValue.objects.create(
                value=i,
                meaning="test permissible meaning %d" % i,
                order=i,
                valueDomain=self.item1
            )
        for i, j in zip(range(3), range(3)):
            # give the item 2 object classes an offset
            models.PermissibleValue.objects.create(
                value=i + j,
                meaning="test permissible meaning %d" % i,
                order=i,
                valueDomain=self.item2
            )
        for i in range(2):
            models.SupplementaryValue.objects.create(
                value=i,
                meaning="test supplementary meaning %d" % i,
                order=i,
                valueDomain=self.item1
            )
