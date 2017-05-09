from django import VERSION as django_version
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings
from django.test.utils import setup_test_environment
from django.utils import timezone
from django.contrib.auth.models import User

import aristotle_mdr.models as models
import aristotle_mdr.perms as perms
from aristotle_mdr.utils import url_slugify_concept
from aristotle_mdr.forms.creation_wizards import WorkgroupVerificationMixin,CheckIfModifiedMixin

setup_test_environment()
from aristotle_mdr.tests import utils
import datetime

class TestNotifications(utils.LoggedInViewPages, TestCase):
    defaults = {}
    def setUp(self):
        super(TestNotifications, self).setUp()

        self.item1 = models.ObjectClass.objects.create(
            name="Test Item 1 (visible to tested viewers)",
            definition="my definition",
            workgroup=self.wg1,
        )
        self.item2 = models.ObjectClass.objects.create(
            name="Test Item 2 (NOT visible to tested viewers)",
            definition="my definition",
            workgroup=self.wg2,
        )
        self.item3 = models.ObjectClass.objects.create(
            name="Test Item 3 (visible to tested viewers)",
            definition="my definition",
            workgroup=self.wg1,
        )

    def test_subscriber_is_notified_of_supersede(self):
        user1 = User.objects.create_user('subscriber','subscriber')
        user1.profile.favourites.add(self.item1)
        self.assertTrue(user1.profile in self.item1.favourited_by.all())

        self.assertEqual(user1.notifications.all().count(), 0)
        kwargs = {}
        if django_version > (1, 9):
            kwargs = {'bulk': False}
        self.item2.supersedes.add(self.item1, **kwargs)

        self.assertTrue(self.item1.superseded_by == self.item2)
        
        user1 = User.objects.get(pk=user1.pk)
        self.assertEqual(user1.notifications.all().count(), 1)
        self.assertTrue('favourited item has been superseded' in user1.notifications.first().verb )

    def test_subscriber_is_notified_of_supersede_via_deprecate_page(self):
        user1 = User.objects.create_user('subscriber','subscriber')
        user1.profile.favourites.add(self.item1)
        self.assertTrue(user1.profile in self.item1.favourited_by.all())

        self.assertEqual(user1.notifications.all().count(), 0)

        self.login_superuser()
        response = self.client.post(
            reverse('aristotle:deprecate',args=[self.item2.id]),{'olderItems':[self.item1.id]})
        self.assertEqual(response.status_code,302)
        
        self.item1 = models.ObjectClass.objects.get(id=self.item1.id) # Stupid cache

        self.assertTrue(self.item1.superseded_by == self.item2.concept)
        
        user1 = User.objects.get(pk=user1.pk)
        self.assertEqual(user1.notifications.all().count(), 1)
        self.assertTrue('favourited item has been superseded' in user1.notifications.first().verb )



    def test_registrar_is_notified_of_supersede(self):
        models.Status.objects.create(
                concept=self.item1,
                registrationAuthority=self.ra,
                registrationDate=datetime.date(2015,4,28),
                state=self.ra.locked_state
                )
        user1 = self.registrar
        user1.notifications.all().delete()

        self.assertEqual(user1.notifications.all().count(), 0)
        kwargs = {}
        if django_version > (1, 9):
            kwargs = {'bulk': False}
        self.item2.supersedes.add(self.item1, **kwargs)

        self.assertTrue(self.item1.superseded_by == self.item2)
        self.assertEqual(user1.notifications.all().count(), 1)
        self.assertTrue('item registered by your registration authority has been superseded' in user1.notifications.first().verb )


    def test_registrar_is_notified_of_status_change(self):
        user1 = self.registrar
        user1.notifications.all().delete()

        self.assertEqual(user1.notifications.all().count(), 0)

        models.Status.objects.create(
                concept=self.item1,
                registrationAuthority=self.ra,
                registrationDate=timezone.now(),
                state=self.ra.locked_state
                )

        self.assertEqual(user1.notifications.all().count(), 1)
        self.assertTrue('item has been registered by your registration authority' in user1.notifications.first().verb )

        models.Status.objects.create(
                concept=self.item1,
                registrationAuthority=self.ra,
                registrationDate=timezone.now(),
                state=self.ra.public_state
                )

        self.assertEqual(user1.notifications.all().count(), 2)
        self.assertTrue('item registered by your registration authority has changed status' in user1.notifications.first().verb )
