from django.conf import settings
from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings, modify_settings
from django.test.utils import setup_test_environment
from django.contrib.auth.models import User
from django.utils.timezone import now
import datetime

from reversion import revisions as reversion

from aristotle_mdr.contrib.self_publish import models as pub
from aristotle_mdr.forms.search import PermissionSearchQuerySet
from aristotle_mdr.models import ObjectClass, Workgroup
from aristotle_mdr.tests import utils
setup_test_environment()


@override_settings(
    ARISTOTLE_SETTINGS=dict(
        settings.ARISTOTLE_SETTINGS,
        EXTRA_CONCEPT_QUERYSETS={
            'visible': ['aristotle_mdr.contrib.self_publish.models.concept_visibility_query'],
            'public': ['aristotle_mdr.contrib.self_publish.models.concept_public_query']
        }
    )
)
class TestSelfPublishing(utils.LoggedInViewPages, TestCase):
    def setUp(self):
        super(TestSelfPublishing, self).setUp()
        self.submitting_user = User.objects.create_user(
            username="self-publisher",
            email="self@publisher.net",
            password="self-publisher")
        with reversion.create_revision():
            self.item = ObjectClass.objects.create(
                name="A self-published item",
                definition="test",
                submitter=self.submitting_user
            )

    def tearDown(self):
        call_command('clear_index', interactive=False, verbosity=0)

    def test_self_publish_queryset_anon(self):
        self.logout()
        response = self.client.get(self.item.get_absolute_url())
        self.assertTrue(response.status_code == 302)

        self.item = ObjectClass.objects.get(pk=self.item.pk)
        self.assertFalse(self.item._is_public)

        psqs = PermissionSearchQuerySet()
        psqs = psqs.auto_query('published').apply_permission_checks()

        self.assertEqual(len(psqs), 0)

        pub.PublicationRecord.objects.create(
            user=self.submitting_user,
            concept=self.item,
            visibility=pub.PublicationRecord.VISIBILITY.public
        )

        response = self.client.get(self.item.get_absolute_url())
        self.assertTrue(response.status_code == 200)

        self.item = ObjectClass.objects.get(pk=self.item.pk)
        self.assertTrue(self.item._is_public)

        psqs = PermissionSearchQuerySet()
        psqs = psqs.auto_query('published').apply_permission_checks()
        self.assertEqual(len(psqs), 1)

    def test_anon_cannot_view_self_publish(self):
        self.logout()
        response = self.client.get(
            reverse('aristotle_self_publish:publish_metadata', args=[self.item.pk])
        )
        self.assertTrue(response.status_code == 302)

    def login_publisher(self):
        self.logout()
        return self.client.post(reverse('friendly_login'), {'username': 'self-publisher', 'password': 'self-publisher'})

    def test_submitter_can_self_publish(self):
        self.login_publisher()
        response = self.client.get(
            reverse('aristotle_self_publish:publish_metadata', args=[self.item.pk])
        )
        self.assertTrue(response.status_code == 200)

        self.item = ObjectClass.objects.get(pk=self.item.pk)
        self.assertFalse(self.item._is_public)

        response = self.client.post(
            reverse('aristotle_self_publish:publish_metadata', args=[self.item.pk]),
            {
                "note": "Published",
                "publication_date": (now() - datetime.timedelta(days=1)).date().isoformat(),
                "visibility": pub.PublicationRecord.VISIBILITY.public
            }
        )
        self.assertTrue(response.status_code == 302)

        self.item = ObjectClass.objects.get(pk=self.item.pk)
        self.assertTrue(self.item._is_public)

        self.logout()
        response = self.client.get(self.item.get_absolute_url())
        self.assertTrue(response.status_code == 200)

        self.login_publisher()
        the_future = (now() + datetime.timedelta(days=100)).date().isoformat()
        response = self.client.post(
            reverse('aristotle_self_publish:publish_metadata', args=[self.item.pk]),
            {
                "note": "Published",
                "publication_date": the_future,
                "visibility": pub.PublicationRecord.VISIBILITY.public
            }
        )
        self.assertTrue(response.status_code == 302)

        self.item = ObjectClass.objects.get(pk=self.item.pk)
        self.assertFalse(self.item._is_public)

        self.logout()
        response = self.client.get(self.item.get_absolute_url())
        self.assertTrue(response.status_code == 302)

        response = self.client.post(
            reverse('aristotle_self_publish:publish_metadata', args=[self.item.pk]),
            {
                "note": "Published",
                "publication_date": now().date().isoformat(),
                "visibility": pub.PublicationRecord.VISIBILITY.hidden
            }
        )
        self.assertTrue(response.status_code == 302)

        self.item = ObjectClass.objects.get(pk=self.item.pk)
        self.assertFalse(self.item._is_public)

        self.logout()
        response = self.client.get(self.item.get_absolute_url())
        self.assertTrue(response.status_code == 302)

    def test_submitter_can_see_hidden_self_publish(self):
        pub.PublicationRecord.objects.create(
            user=self.submitting_user,
            concept=self.item,
            visibility=pub.PublicationRecord.VISIBILITY.active
        )

        self.assertTrue(
            self.item.__class__.objects.all().visible(self.registrar).filter(pk=self.item.pk).exists()
        )
