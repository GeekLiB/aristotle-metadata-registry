from django.test import TestCase

import aristotle_mdr.tests.utils as utils
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.template import TemplateDoesNotExist
from aristotle_mdr.tests.main.test_html_pages import LoggedInViewConceptPages
from aristotle_mdr.tests.main.test_admin_pages import AdminPageForConcept

from extension_test.models import Question, Questionnaire

from django.test.utils import setup_test_environment
setup_test_environment()


class TestExtensionListVisibility(TestCase):
    def test_extension_list_page(self):
        from django.apps import apps

        response = self.client.get(reverse('aristotle_mdr:extensions'))
        self.assertEqual(response.status_code, 200)
        ext = apps.get_app_config('extension_test')
        download = apps.get_app_config('text_download_test')
        self.assertContains(response, download.verbose_name)
        self.assertTrue('text_download_test' in response.context['download_extensions'].keys())
        self.assertContains(response, ext.verbose_name)
        self.assertTrue(ext in response.context['content_extensions'])


class QuestionVisibility(utils.ManagedObjectVisibility, TestCase):
    def setUp(self):
        super(QuestionVisibility, self).setUp()
        self.item = Question.objects.create(
            name="Test Question",
            workgroup=self.wg,
        )

class QuestionAdmin(AdminPageForConcept, TestCase):
    itemType=Question


class LoggedInViewExtensionConceptPages(LoggedInViewConceptPages):
    def get_help_page(self):
        return reverse('extension_test:about', args=[self.item1._meta.model_name])


class QuestionViewPage(LoggedInViewExtensionConceptPages, TestCase):
    url_name='question'
    itemType=Question

    def test_help_page_exists(self):
        self.logout()
        response = self.client.get(self.get_help_page())
        self.assertEqual(response.status_code, 200)
        

# ---- Questionnaire tests


class QuestionnaireVisibility(utils.ManagedObjectVisibility, TestCase):
    def setUp(self):
        super(QuestionnaireVisibility, self).setUp()
        self.item = Questionnaire.objects.create(
            name="Test Question",
            workgroup=self.wg,
        )


class QuestionnaireAdmin(AdminPageForConcept, TestCase):
    itemType=Questionnaire

    def test_registry_autofields(self):
        self.login_editor()
        response = self.client.get(reverse(
            "admin:%s_%s_change" % (
                self.itemType._meta.app_label,
                self.itemType._meta.model_name
            ),
            args=[self.item1.pk]
        ))
        self.assertResponseStatusCodeEqual(response, 200)
        # print dir(response.context['adminform'].model_admin)

        auto_fields = response.context['adminform'].model_admin.fieldsets[-1]
        self.assertEqual(auto_fields[0], u'Extra fields for Questionnaire')
        self.assertTrue('start_date' in auto_fields[1]['fields'])
        self.assertTrue('end_date' in auto_fields[1]['fields'])
        self.assertTrue('questions' in auto_fields[1]['fields'])


class QuestionnaireViewPage(LoggedInViewExtensionConceptPages, TestCase):
    url_name='item'  # 'questionnaire' # the lazy way
    itemType=Questionnaire

    def test_help_page_exists(self):
        self.logout()

        with self.assertRaises(TemplateDoesNotExist):
            # They never made this help page, this will error
            response = self.client.get(self.get_help_page())

    def test_questions_not_on_edit_screen(self):
        self.login_editor()
        response = self.client.get(reverse('aristotle:edit_item', args=[self.item1.id]))
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertTrue('questions' not in form.fields)

    def test_questions_attachment_editor(self):
        self.login_editor()
        response = self.client.get(reverse('extension_test:questionnaire_add_question', args=[self.item1.id]))
        self.assertEqual(response.status_code, 200)
        form = response.context['form']


    def loggedin_user_can_use_value_page(self,value_url,current_item,http_code):
        response = self.client.get(reverse(value_url,args=[current_item.id]))
        self.assertEqual(response.status_code,http_code)

    def test_submitter_can_use_generic_m2m_edit_page(self):
        value_url = "extension_test:questionnaire_add_question"
        self.login_editor()
        self.loggedin_user_can_use_value_page(value_url,self.item1,200)
        self.loggedin_user_can_use_value_page(value_url,self.item2,403)
        self.loggedin_user_can_use_value_page(value_url,self.item3,200)

        data = {}
        num_vals = self.item1.questions.count()
        self.assertTrue(num_vals == 0)

        q1 = Question.objects.create(name="Q1",definition="Q1",submitter=self.editor)
        q2 = Question.objects.create(name="Q2",definition="Q2",submitter=self.editor)
        q3 = Question.objects.create(name="Q3",definition="Q3")
        
        
        response = self.client.post(
            reverse(value_url,args=[self.item1.id]),
            {"items_to_add":[q1.pk,q2.pk,q3.pk],}
        )

        self.assertContains(response, 'Select a valid choice')
        self.item1 = Questionnaire.objects.get(pk=self.item1.pk)
        self.assertTrue(self.item1.questions.count() == 0)

        response = self.client.post(
            reverse(value_url,args=[self.item1.id]),
            {"items_to_add":[q1.pk,q2.pk],}
        )

        self.item1 = Questionnaire.objects.get(pk=self.item1.pk)

        self.assertTrue(self.item1.questions.count() > 0)
        self.assertTrue(q1 in self.item1.questions.all())
        self.assertTrue(q2 in self.item1.questions.all())
        self.assertTrue(q3 not in self.item1.questions.all())

    def test_datefield_in_editor(self):
        self.login_editor()
        response = self.client.get(reverse('aristotle:edit_item', args=[self.item1.id]))
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertContains(response, 'glyphicon-calendar')  # While we use bootstrap-datewidget, this should be there.

