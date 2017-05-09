from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings, modify_settings
from django.test.utils import setup_test_environment

from django.core.management import call_command
from aristotle_mdr.contrib.help import models
from aristotle_mdr.utils import fetch_aristotle_settings

setup_test_environment()


def setUpModule():
    # There are race contitions around ordering of help loading
    # So lets just clear everything out!
    models.HelpPage.objects.all().delete()
    models.ConceptHelp.objects.all().delete()


class TestHelpPagesLoad(TestCase):
    def test_help_pages_load_into_db(self):
        count_hp_1 = models.HelpPage.objects.all().count()
        count_cp_1 = models.ConceptHelp.objects.all().count()

        call_command('load_aristotle_help')

        count_hp_2 = models.HelpPage.objects.all().count()
        count_cp_2 = models.ConceptHelp.objects.all().count()
        self.assertTrue(count_hp_2 > count_hp_1)
        self.assertTrue(count_cp_2 > count_cp_1)

    def test_help_pages_load_into_db_with_update(self):
        call_command('load_aristotle_help')
        count_hp_1 = models.HelpPage.objects.all().count()
        page = models.HelpPage.objects.get(title="Advanced Search")

        nixons_shiny_new_body = "I paid for this body and I'd no sooner return it than I would my little cocker spaniel dog, Checkers."
        page.body = nixons_shiny_new_body
        page.save()
        page = models.HelpPage.objects.get(title="Advanced Search")  # de-cache
        self.assertTrue(page.body == nixons_shiny_new_body)

        call_command('load_aristotle_help', update=False)
        count_hp_2 = models.HelpPage.objects.all().count()
        self.assertTrue(count_hp_2 == count_hp_1)

        page = models.HelpPage.objects.get(title="Advanced Search")  # de-cache
        self.assertTrue(page.body == nixons_shiny_new_body)

        call_command('load_aristotle_help', update=True)
        count_hp_3 = models.HelpPage.objects.all().count()

        self.assertTrue(count_hp_3 == count_hp_1)

        page = models.HelpPage.objects.get(title="Advanced Search")  # de-cache
        self.assertTrue(page.body != nixons_shiny_new_body)

    def test_help_pages_load(self):
        call_command('load_aristotle_help')
        regular_help = models.HelpPage.objects.all()
        concept_help = models.ConceptHelp.objects.all()

        response = self.client.get(reverse('aristotle_help:help_base'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('aristotle_help:help_concepts'))
        self.assertEqual(response.status_code, 200)

        for app_label in fetch_aristotle_settings()['CONTENT_EXTENSIONS']:
            response = self.client.get(reverse('aristotle_help:concept_app_help', args=[app_label]))
            self.assertEqual(response.status_code, 200)

        for obj in concept_help:
            response = self.client.get(reverse('aristotle_help:concept_help', args=[obj.app_label, obj.concept_type]))
            self.assertEqual(response.status_code, 200)

        for obj in concept_help:
            response = self.client.get(reverse('aristotle_help:concept_help', args=[obj.app_label, obj.concept_type]))
            self.assertEqual(response.status_code, 200)

        for obj in regular_help:
            response = self.client.get(reverse('aristotle_help:help_page', args=[obj.slug]))
            self.assertEqual(response.status_code, 200)

    def test_bad_help_template_tags(self):
        from aristotle_mdr.contrib.help.templatetags import aristotle_help as tags

        page = models.HelpPage()

        rendered = tags.relink(page, 'body')
        self.assertTrue(rendered == "")

        page = models.HelpPage(
            body="[[some_page]]"
        )

        rendered = tags.relink(page, 'body')
        self.assertTrue('unknown model' in rendered)

        page = models.HelpPage(
            body="[[h|some_page]]"
        )

        rendered = tags.relink(page, 'body')
        self.assertTrue('unknown help page' in rendered)

    def test_good_help_template_tags(self):
        from aristotle_mdr.contrib.help.templatetags import aristotle_help as tags

        page = models.HelpPage(
            body="[[aristotle_mdr.Property|s]]"
        )

        rendered = tags.relink(page, 'body')
        self.assertTrue('Properties' in rendered)

        rendered = tags.relink_f(page.body)
        self.assertTrue('Properties' in rendered)

        page = models.HelpPage(
            body="[[aristotle_mdr.Property|su]]"
        )

        rendered = tags.relink(page, 'body')
        self.assertTrue('Properties' not in rendered)
        self.assertTrue('class=\'help_link' not in rendered)
        self.assertTrue('aristotle_mdr/property' in rendered)

        rendered = tags.relink_f(page.body)
        self.assertTrue('Properties' not in rendered)
        self.assertTrue('class=\'help_link' not in rendered)
        self.assertTrue('aristotle_mdr/property' in rendered)

        page = models.HelpPage.objects.create(
            title="myslug",
            body=""
        )

        page = models.HelpPage(
            body="[[h|myslug]]"
        )

        rendered = tags.relink(page, 'body')
        self.assertTrue('myslug' in rendered)
        self.assertTrue('class=\'help_link' in rendered)

        rendered = tags.relink_f(page.body)
        self.assertTrue('myslug' in rendered)
        self.assertTrue('class=\'help_link' in rendered)

        page = models.HelpPage(
            body="[[h|myslug|u]]"
        )

        rendered = tags.relink(page, 'body')
        self.assertTrue('myslug' in rendered)
        self.assertTrue('class=\'help_link' not in rendered)
