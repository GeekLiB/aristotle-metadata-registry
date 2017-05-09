from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings
from django.test.utils import setup_test_environment
from django.utils import timezone

import aristotle_mdr.models as models
import aristotle_mdr.perms as perms
from aristotle_mdr.utils import url_slugify_concept
from aristotle_mdr.tests.utils import get_json_from_response

setup_test_environment()
from aristotle_mdr.tests import utils
import datetime


class LoggedInConceptAutocompletes(utils.LoggedInViewPages, TestCase):
    defaults = {}

    def test_concept_autocompletes(self):
        self.logout()

        item1 = models.ObjectClass.objects.create(name="Test Item 1 (visible to tested viewers)",definition="my definition",workgroup=self.wg1,**self.defaults)
        item2 = models.ObjectClass.objects.create(name="Test Item 2 (NOT visible to tested viewers)",definition="my definition",workgroup=self.wg2,**self.defaults)

        response = self.client.get(
            reverse("aristotle-autocomplete:concept")
        )

        data = utils.get_json_from_response(response)
        self.assertEqual(len(data['results']), 0)

        self.login_superuser()
        response = self.client.get(
            reverse("aristotle-autocomplete:concept")
        )
        data = utils.get_json_from_response(response)
        self.assertEqual(len(data['results']), 2)

        response = self.client.get(
            reverse("aristotle-autocomplete:concept") + "?q=Not"  # Test case insensitivity
        )
        data = utils.get_json_from_response(response)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(str(data['results'][0]['id']), str(item2.id))

    def test_concept_identifier_autocompletes(self):
        self.logout()

        item1 = models.ObjectClass.objects.create(name="Test Item 1 (visible to tested viewers)",definition="my definition",workgroup=self.wg1,**self.defaults)
        org = models.Organization.objects.create(name='My org', definition="None")
        from aristotle_mdr.contrib.identifiers.models import ScopedIdentifier, Namespace
        ns = Namespace.objects.create(naming_authority=org, shorthand_prefix='my_org')
        ScopedIdentifier.objects.create(namespace=ns,concept=item1,identifier="my_ident")

        self.login_superuser()
        response = self.client.get(
            reverse("aristotle-autocomplete:concept") + "?q=my_id" # test partial fails
        )
        data = utils.get_json_from_response(response)
        self.assertEqual(len(data['results']), 0)

        response = self.client.get(
            reverse("aristotle-autocomplete:concept") + "?q=my_ident"
        )
        data = utils.get_json_from_response(response)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(str(data['results'][0]['id']), str(item1.id))



class LoggedInUserAutocompletes(utils.LoggedInViewPages, TestCase):
    def setUp(self, *args, **kwargs):
        super(LoggedInUserAutocompletes, self).setUp(*args, **kwargs)
        before_count = User.objects.all().count()
        self.dwarves = ["Doc","Grumpy","Happy","Sleepy","Bashful","Sneezy","Dopey"]

        self.dwarf_users = [
            User.objects.create(username=dwarf, email="%s@dwarves.mine"%dwarf.lower())
            for dwarf in self.dwarves
        ]

        self.assertEqual(User.objects.all().count()-before_count, len(self.dwarf_users))

    def test_user_autocomplete_anon(self):
        response = self.client.get(
            reverse("aristotle-autocomplete:user")
        )
        self.assertEqual(response.status_code, 403)

    def test_user_autocomplete_editor(self):

        self.login_editor()
        response = self.client.get(
            reverse("aristotle-autocomplete:user")
        )
        self.assertEqual(response.status_code, 403)

    def test_user_autocomplete_registrar(self):
        self.login_registrar()
        response = self.client.get(
            reverse("aristotle-autocomplete:user")
        )
        data = get_json_from_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['results'], [])

        response = self.client.get(
            reverse("aristotle-autocomplete:user")+"?q=Grump",
        )
        data = get_json_from_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['results']), 0)

        response = self.client.get(
            reverse("aristotle-autocomplete:user")+"?q=Grumpy",
        )
        data = get_json_from_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['text'], 'Grumpy')

        response = self.client.get(
            reverse("aristotle-autocomplete:user")+"?q=grumpy@dwarves.mine",
        )
        data = get_json_from_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['text'], 'Grumpy')

    def test_user_autocomplete_workgroup_manager(self):
        self.login_manager()
        response = self.client.get(
            reverse("aristotle-autocomplete:user")
        )
        data = get_json_from_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['results'], [])

        response = self.client.get(
            reverse("aristotle-autocomplete:user")+"?q=Grump",
        )
        data = get_json_from_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['results']), 0)

        response = self.client.get(
            reverse("aristotle-autocomplete:user")+"?q=Grumpy",
        )
        data = get_json_from_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['text'], 'Grumpy')

        response = self.client.get(
            reverse("aristotle-autocomplete:user")+"?q=grumpy@dwarves.mine",
        )
        data = get_json_from_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['text'], 'Grumpy')


    def test_user_autocomplete_superuser(self):
        num_users = User.objects.all().count()
        self.login_superuser()
        response = self.client.get(
            reverse("aristotle-autocomplete:user")
        )
        data = get_json_from_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['results']), min(10, num_users))  # Autocomplete retuns a max of 10 results

        response = self.client.get(
            reverse("aristotle-autocomplete:user")+"?q=Grump",
        )
        data = get_json_from_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['text'], 'Grumpy')

        response = self.client.get(
            reverse("aristotle-autocomplete:user")+"?q=Grumpy",
        )
        data = get_json_from_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['text'], 'Grumpy')

        response = self.client.get(
            reverse("aristotle-autocomplete:user")+"?q=grumpy@dwarves.mine",
        )
        data = get_json_from_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['text'], 'Grumpy')

        response = self.client.get(
            reverse("aristotle-autocomplete:user")+"?q=@dwarves.mine",
        )
        data = get_json_from_response(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['results']), len(self.dwarves))
