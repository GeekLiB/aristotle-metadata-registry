from django.test import TestCase
from django.utils import timezone
from django.core.urlresolvers import reverse
from django.core.management import call_command

import aristotle_mdr.models as models
import aristotle_mdr.tests.utils as utils
from aristotle_mdr.utils import url_slugify_concept

from django.test.utils import setup_test_environment
setup_test_environment()

class CreateListPageTests(utils.LoggedInViewPages,TestCase):
    def test_create_list_active(self):
        self.logout()
        response = self.client.get(reverse('aristotle:create_list'))
        self.assertEqual(response.status_code,302) # redirect to login

        self.login_viewer()
        response = self.client.get(reverse('aristotle:create_list'))
        self.assertEqual(response.status_code,200)

        self.login_registrar()
        response = self.client.get(reverse('aristotle:create_list'))
        self.assertEqual(response.status_code,200)

        self.login_editor()
        response = self.client.get(reverse('aristotle:create_list'))
        self.assertEqual(response.status_code,200)


class ConceptWizard_TestInvalidUrls(utils.LoggedInViewPages,TestCase):
    def tearDown(self):
        call_command('clear_index', interactive=False, verbosity=0)

    def setUp(self):
        super(ConceptWizard_TestInvalidUrls, self).setUp()
        import haystack
        haystack.connections.reload('default')

    def test_invalid_model(self):
        url = reverse('aristotle:createItem',args=["invalid_model_name"])
        self.login_editor()
        response = self.client.get(url)
        self.assertEqual(response.status_code,404)
        url = reverse('aristotle:createItem',args=["objectclass"])
        response = self.client.get(url)
        self.assertEqual(response.status_code,200)

    def test_invalid_app_and_model(self):
        url = reverse('aristotle:createItem',args=["invalid_app_name","invalid_model_name"])
        self.login_editor()
        response = self.client.get(url)
        self.assertEqual(response.status_code,404)
        url = reverse('aristotle:createItem',args=["aristotle_mdr","objectclass"])
        response = self.client.get(url)
        self.assertEqual(response.status_code,200)



class ConceptWizardPage(utils.LoggedInViewPages):
    wizard_url_name="Harry Potter" # This will break if called without overriding the wizard_url_name. Plus its funny.
    wizard_form_name="dynamic_aristotle_wizard"
    def tearDown(self):
        call_command('clear_index', interactive=False, verbosity=0)

    def setUp(self):
        super(ConceptWizardPage, self).setUp()
        import haystack
        haystack.connections.reload('default')


        # Tests against bug #333
        # https://github.com/aristotle-mdr/aristotle-metadata-registry/issues/333
        self.extra_wg = models.Workgroup.objects.create(name="Extra WG for issue 333")
        self.extra_wg.stewards.add(self.editor)
        self.extra_wg.submitters.add(self.editor)
        self.extra_wg.viewers.add(self.editor)
        self.extra_wg.save()

    @property
    def wizard_url(self):
        return reverse('aristotle:createItem',args=[self.model._meta.app_label,self.model._meta.model_name])

    def test_anonymous_cannot_view_create_page(self):
        self.logout()
        response = self.client.get(self.wizard_url)
        self.assertEqual(response.status_code,302)

    def test_viewer_can_view_create_page(self):
        self.login_viewer()
        response = self.client.get(self.wizard_url)
        self.assertEqual(response.status_code,200)

    def test_regular_user_can_view_create_page(self):
        # Thanks @stevenmce for pointing this out
        self.login_regular_user()
        response = self.client.get(self.wizard_url)
        self.assertEqual(response.status_code,200)

    def test_registrar_cannot_view_create_page(self):
        self.login_registrar()
        response = self.client.get(self.wizard_url)
        self.assertEqual(response.status_code,200)

    def test_editor_can_view_create_page(self):
        self.login_editor()
        response = self.client.get(self.wizard_url)
        self.assertEqual(response.status_code,200)

    def do_test_for_issue333(self,response):
        self.assertContains(response, self.extra_wg.name)
        self.assertTrue(response.content.decode('utf-8').count(self.extra_wg.name) == 1)

    def test_editor_can_make_object(self):
        self.login_editor()
        step_1_data = {
            self.wizard_form_name+'-current_step': 'initial',
        }

        response = self.client.post(self.wizard_url, step_1_data)
        wizard = response.context['wizard']
        self.assertEqual(wizard['steps'].current, 'initial')
        self.assertTrue('name' in wizard['form'].errors.keys())

        # must submit a name
        step_1_data.update({'initial-name':"Test Item"})
        # success!

        response = self.client.post(self.wizard_url, step_1_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wizard['steps'].current, 'results')
        
        self.do_test_for_issue333(response)
        
        step_2_data = {
            self.wizard_form_name+'-current_step': 'results',
            'results-name':"Test Item",
        }

        response = self.client.post(self.wizard_url, step_2_data)
        wizard = response.context['wizard']
        self.assertTrue('definition' in wizard['form'].errors.keys())
        # NOWG self.assertTrue('workgroup' in wizard['form'].errors.keys())

        # no "test item" yet.
        self.assertFalse(models._concept.objects.filter(name="Test Item").exists())

        # must submit a definition at this step. But we are using a non-permitted workgroup.
        step_2_data.update({
            'results-definition':"Test Definition",
            'results-workgroup':self.wg2.id
            })
        response = self.client.post(self.wizard_url, step_2_data)
        self.assertEqual(response.status_code, 200)
        wizard = response.context['wizard']
        self.assertTrue('workgroup' in wizard['form'].errors.keys())

        # must submit a definition at this step. With the right workgroup
        step_2_data.update({
            'results-definition':"Test Definition",
            'results-workgroup':self.wg1.id
            })
        response = self.client.post(self.wizard_url, step_2_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(models._concept.objects.filter(name="Test Item").exists())
        self.assertEqual(models._concept.objects.filter(name="Test Item").count(),1)
        item = models._concept.objects.filter(name="Test Item").first()
        self.assertRedirects(response,url_slugify_concept(item))

class ObjectClassWizardPage(ConceptWizardPage,TestCase):
    model=models.ObjectClass
class PropertyWizardPage(ConceptWizardPage,TestCase):
    model=models.Property
class ValueDomainWizardPage(ConceptWizardPage,TestCase):
    model=models.ValueDomain
#class DataElementWizardPage(ConceptWizardPage,TestCase):
#    model=models.DataElement

class DataElementConceptWizardPage(ConceptWizardPage,TestCase):
    wizard_url_name="createDataElementConcept"
    wizard_form_name="data_element_concept_wizard"
    @property
    def wizard_url(self):
        return reverse('aristotle:%s'%self.wizard_url_name)
    def test_editor_can_make_object(self):
        pass
    def test_editor_can_make_object__has_prior_components(self):
        self.login_editor()
        from reversion.revisions import create_revision
        with create_revision():
            ani = models.ObjectClass.objects.create(name="animagus",definition="my definition",workgroup=self.wg1)
            at  = models.Property.objects.create(name="animal type",definition="my definition",workgroup=self.wg1)

        step_1_data = {
            self.wizard_form_name+'-current_step': 'component_search',
            'component_search-oc_name':"animagus",
            'component_search-pr_name':"animal"
        }
        # success!

        response = self.client.post(self.wizard_url, step_1_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wizard['steps'].current, 'component_results')
        self.assertDelayedEqual(len(wizard['form'].fields.keys()),2) # we should have a match for OC and P

        step_2_data = {}
        step_2_data.update(step_1_data)
        step_2_data.update({self.wizard_form_name+'-current_step': 'component_results'})

        response = self.client.post(self.wizard_url, step_2_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wizard['steps'].current, 'component_results')

        # Must pick an Object Class and Property (or none) to continue.
        self.assertTrue('oc_options' in wizard['form'].errors.keys())
        self.assertTrue('pr_options' in wizard['form'].errors.keys())

        # Try the wrong way around
        step_2_data.update({'component_results-oc_options':at.pk,'component_results-pr_options':ani.pk})
        response = self.client.post(self.wizard_url, step_2_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wizard['steps'].current, 'component_results')
        self.assertTrue('oc_options' in wizard['form'].errors.keys())
        self.assertTrue('pr_options' in wizard['form'].errors.keys())

        # Picking the correct options should send us to the DEC results page.
        step_2_data.update({'component_results-oc_options':str(ani.pk),'component_results-pr_options':str(at.pk)})
        response = self.client.post(self.wizard_url, step_2_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wizard['steps'].current, 'find_dec_results')


    def test_editor_can_make_object__no_prior_components(self):
        self.login_editor()
        step_1_data = {
            self.wizard_form_name+'-current_step': 'component_search',
        }

        response = self.client.post(self.wizard_url, step_1_data)
        wizard = response.context['wizard']
        self.assertEqual(wizard['steps'].current, 'component_search')
        self.assertTrue('oc_name' in wizard['form'].errors.keys())
        self.assertTrue('pr_name' in wizard['form'].errors.keys())

        # must submit a name
        step_1_data.update({'component_search-oc_name':"Animagus"})
        step_1_data.update({'component_search-pr_name':"Animal type"})
        # success!

        response = self.client.post(self.wizard_url, step_1_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wizard['steps'].current, 'component_results')
        self.assertContains(response,"No matching object classes were found")
        self.assertContains(response,"No matching properties were found")

        step_2_data = {
            self.wizard_form_name+'-current_step': 'component_results',
        } # nothing else needed, as we aren't picking a component.

        response = self.client.post(self.wizard_url, step_2_data)
        wizard = response.context['wizard']
        self.assertEqual(wizard['steps'].current, 'make_oc')

        # Now we make the object class
        step_3_data = {
            self.wizard_form_name+'-current_step': 'make_oc',
            'make_oc-name':"Animagus",
        }

        response = self.client.post(self.wizard_url, step_3_data)
        wizard = response.context['wizard']
        self.assertTrue('definition' in wizard['form'].errors.keys())
        # NOWG self.assertTrue('workgroup' in wizard['form'].errors.keys())

        # no "test item" yet.
        self.assertFalse(models._concept.objects.filter(name="Test Item").exists())

        # must submit a definition at this step. But we are using a non-permitted workgroup.
        step_3_data.update({
            'make_oc-definition':"A wizard who can change shape.",
            'make_oc-workgroup':self.wg2.id
            })
        response = self.client.post(self.wizard_url, step_3_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertTrue('workgroup' in wizard['form'].errors.keys())

        # must submit a definition at this step. With the right workgroup
        step_3_data.update({
            'make_oc-workgroup':self.wg1.id
            })
        response = self.client.post(self.wizard_url, step_3_data)
        self.assertEqual(response.status_code, 200)
        wizard = response.context['wizard']
        self.assertEqual(wizard['steps'].current, 'make_p')

        # Now we make the property
        step_4_data = {
            self.wizard_form_name+'-current_step': 'make_p',
            'make_p-name':"Animal type",
        }

        response = self.client.post(self.wizard_url, step_4_data)
        wizard = response.context['wizard']
        self.assertTrue('definition' in wizard['form'].errors.keys())
        # NOWG self.assertTrue('workgroup' in wizard['form'].errors.keys())

        # no "test item" yet.
        self.assertFalse(models._concept.objects.filter(name="Test Item").exists())

        # must submit a definition at this step. But we are using a non-permitted workgroup.
        step_4_data.update({
            'make_p-definition':"A wizard who can change shape.",
            'make_p-workgroup':self.wg2.pk
            })
        response = self.client.post(self.wizard_url, step_4_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertTrue('workgroup' in wizard['form'].errors.keys())

        # must submit a definition at this step. With the right workgroup
        step_4_data.update({
            'make_p-workgroup':self.wg1.pk
            })
        response = self.client.post(self.wizard_url, step_4_data)
        self.assertEqual(response.status_code, 200)
        wizard = response.context['wizard']
        self.assertEqual(wizard['steps'].current, 'find_dec_results')

        step_4_data.update(step_3_data)
        self.assertEqual(response.status_code, 200)
        wizard = response.context['wizard']
        self.assertEqual(response.context['form'].initial['name'], 'Animagus--Animal type')

        step_5_data = {}
        step_5_data.update(step_4_data)
        step_5_data.update({self.wizard_form_name+'-current_step': 'find_dec_results',})

        response = self.client.post(self.wizard_url, step_5_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertTrue('name' in wizard['form'].errors.keys())
        self.assertTrue('definition' in wizard['form'].errors.keys())
        # NOWG self.assertTrue('workgroup' in wizard['form'].errors.keys())

        # must submit a name and definition at this step. But we are using a non-permitted workgroup.
        step_5_data.update({
            'find_dec_results-name':"Animagus--Animal type",
            'find_dec_results-definition':"The record of the shape a wizard can change into.",
            'find_dec_results-workgroup':self.wg2.pk
            })
        response = self.client.post(self.wizard_url, step_5_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertTrue('workgroup' in wizard['form'].errors.keys())

        # must submit a definition at this step. With the right workgroup
        step_5_data.update({
            'find_dec_results-workgroup':self.wg1.pk
            })
        response = self.client.post(self.wizard_url, step_5_data)
        self.assertEqual(response.status_code, 200)
        wizard = response.context['wizard']
        self.assertEqual(wizard['steps'].current, 'completed')


        # now save everything
        step_6_data = {}
        step_6_data.update(step_5_data)
        step_6_data.update({
            self.wizard_form_name+'-current_step': 'completed',
        })

        response = self.client.post(self.wizard_url, step_6_data)
        wizard = response.context['wizard']
        self.assertTrue('make_items' in wizard['form'].errors.keys())
        self.assertFalse(models.DataElementConcept.objects.filter(name="Animagus--Animal type").exists())
        step_6_data.update({
            self.wizard_form_name+'-current_step': 'completed',
            'completed-make_items':True
            })
        response = self.client.post(self.wizard_url, step_6_data)
        self.assertTrue(models.DataElementConcept.objects.filter(name="Animagus--Animal type").exists())
        item = models.DataElementConcept.objects.filter(name="Animagus--Animal type").first()
        self.assertRedirects(response,url_slugify_concept(item))


class DataElementWizardPage(ConceptWizardPage,TestCase):
    wizard_url_name="createDataElement"
    wizard_form_name="data_element_wizard"
    @property
    def wizard_url(self):
        return reverse('aristotle:%s'%self.wizard_url_name)
    def test_editor_can_make_object(self):
        pass
    def test_editor_can_make_object__has_prior_components(self):
        self.login_editor()

        from reversion.revisions import create_revision
        with create_revision():
            ani   = models.ObjectClass.objects.create(name="animagus",definition="my definition",workgroup=self.wg1)
            at    = models.Property.objects.create(name="animal type",definition="my definition",workgroup=self.wg1)
            momat = models.ValueDomain.objects.create(name="MoM animal type classification",
                    definition="Ministry of Magic standard classification of animagus animal types",workgroup=self.wg1)
            ani_dec = models.DataElementConcept.objects.create(
                name="animagus--animal type",
                definition="my definition",
                workgroup=self.wg1,
                objectClass=ani,
                property=at
            )

        step_1_data = {
            self.wizard_form_name+'-current_step': 'component_search',
            'component_search-oc_name':"animagus",
            'component_search-pr_name':"animal",
            'component_search-vd_name':"mom classification"
        }
        # success!

        response = self.client.post(self.wizard_url, step_1_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wizard['steps'].current, 'component_results')
        self.assertDelayedEqual(len(wizard['form'].fields.keys()),3) # we should have a match for OC, P and VD

        step_2_data = {}
        step_2_data.update(step_1_data)
        step_2_data.update({self.wizard_form_name+'-current_step': 'component_results'})

        response = self.client.post(self.wizard_url, step_2_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wizard['steps'].current, 'component_results')

        # Must pick an Object Class and Property (or none) to continue.
        self.assertTrue('oc_options' in wizard['form'].errors.keys())
        self.assertTrue('pr_options' in wizard['form'].errors.keys())
        self.assertTrue('vd_options' in wizard['form'].errors.keys())

        # Try the wrong way around
        step_2_data.update({'component_results-oc_options':at.pk,'component_results-pr_options':momat.pk,'component_results-vd_options':ani.pk})
        response = self.client.post(self.wizard_url, step_2_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wizard['steps'].current, 'component_results')
        self.assertTrue('oc_options' in wizard['form'].errors.keys())
        self.assertTrue('pr_options' in wizard['form'].errors.keys())
        self.assertTrue('vd_options' in wizard['form'].errors.keys())

        # Picking the correct options should send us to the DEC results page.
        step_2_data.update({'component_results-oc_options':str(ani.pk),
                            'component_results-pr_options':str(at.pk),
                            'component_results-vd_options':str(momat.pk)})
        response = self.client.post(self.wizard_url, step_2_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wizard['steps'].current, 'find_dec_results') # There is a matching DEC
        step_3_data = {}
        step_3_data.update(step_2_data)
        step_3_data.update({self.wizard_form_name+'-current_step': 'find_dec_results'})
        response = self.client.post(self.wizard_url, step_3_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wizard['steps'].current, 'find_dec_results')

    def test_editor_can_make_object__has_prior_components_but_no_dec(self):
        self.login_editor()
        from reversion.revisions import create_revision
        with create_revision():
            ani   = models.ObjectClass.objects.create(name="animagus",definition="my definition",workgroup=self.wg1)
            at    = models.Property.objects.create(name="animal type",definition="my definition",workgroup=self.wg1)
            momat = models.ValueDomain.objects.create(name="MoM animal type classification",
                    definition="Ministry of Magic standard classification of animagus animal types",workgroup=self.wg1)

        step_1_data = {
            self.wizard_form_name+'-current_step': 'component_search',
            'component_search-oc_name':"animagus",
            'component_search-pr_name':"animal",
            'component_search-vd_name':"mom classification"
        }
        # success!

        response = self.client.post(self.wizard_url, step_1_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wizard['steps'].current, 'component_results')
        self.assertDelayedEqual(len(wizard['form'].fields.keys()),3) # we should have a match for OC, P and VD

        step_2_data = {}
        step_2_data.update(step_1_data)
        step_2_data.update({self.wizard_form_name+'-current_step': 'component_results'})

        response = self.client.post(self.wizard_url, step_2_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wizard['steps'].current, 'component_results')

        # Must pick an Object Class and Property (or none) to continue.
        self.assertTrue('oc_options' in wizard['form'].errors.keys())
        self.assertTrue('pr_options' in wizard['form'].errors.keys())
        self.assertTrue('vd_options' in wizard['form'].errors.keys())

        # Try the wrong way around
        step_2_data.update({'component_results-oc_options':at.pk,'component_results-pr_options':momat.pk,'component_results-vd_options':ani.pk})
        response = self.client.post(self.wizard_url, step_2_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wizard['steps'].current, 'component_results')
        self.assertTrue('oc_options' in wizard['form'].errors.keys())
        self.assertTrue('pr_options' in wizard['form'].errors.keys())
        self.assertTrue('vd_options' in wizard['form'].errors.keys())

        # Picking the correct options should send us to the DEC results page.
        step_2_data.update({'component_results-oc_options':str(ani.pk),
                            'component_results-pr_options':str(at.pk),
                            'component_results-vd_options':str(momat.pk)})
        response = self.client.post(self.wizard_url, step_2_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wizard['steps'].current, 'make_dec') # Jump straight to make DEC, as no matching will be found.

        # Now we make the Data Element Concept
        step_3_data = {}
        step_3_data.update(step_2_data)
        step_3_data = {
            self.wizard_form_name+'-current_step': 'make_dec',
            'make_dec-name':"Animagus--Animal type",
        }

        response = self.client.post(self.wizard_url, step_3_data)
        wizard = response.context['wizard']
        self.assertTrue('definition' in wizard['form'].errors.keys())
        # NOWG self.assertTrue('workgroup' in wizard['form'].errors.keys())

        # no "test item" yet.
        self.assertFalse(models.DataElementConcept.objects.filter(name="Animagus--Animal type").exists())

        # must submit a definition at this step. But we are using a non-permitted workgroup.
        step_3_data.update({
            'make_dec-definition':"The record of the shape a wizard can change into.",
            'make_dec-workgroup':self.wg2.pk
            })
        response = self.client.post(self.wizard_url, step_3_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertTrue('workgroup' in wizard['form'].errors.keys())

        # must submit a definition at this step. With the right workgroup
        step_3_data.update({
            'make_dec-workgroup':self.wg1.id
            })
        response = self.client.post(self.wizard_url, step_3_data)
        self.assertEqual(response.status_code, 200)
        wizard = response.context['wizard']
        self.assertEqual(wizard['steps'].current, 'find_de_results')

        # Now we make the Data Element
        step_4_data = {}
        step_4_data.update(step_3_data)
        step_4_data = {
            self.wizard_form_name+'-current_step': 'find_de_results',
            'find_de_results-name':"Animagus--Animal type, MoM Code",
        }

        response = self.client.post(self.wizard_url, step_4_data)
        wizard = response.context['wizard']
        self.assertTrue('definition' in wizard['form'].errors.keys())
        # NOWG self.assertTrue('workgroup' in wizard['form'].errors.keys())

        # no "test item" yet.
        self.assertFalse(models.DataElement.objects.filter(name="Animagus--Animal type, MoM Code").exists())

        # must submit a definition at this step. But we are using a non-permitted workgroup.
        step_4_data.update({
            'find_de_results-definition':"The record of the shape a wizard can change into.",
            'find_de_results-workgroup':self.wg2.pk
            })
        response = self.client.post(self.wizard_url, step_4_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertTrue('workgroup' in wizard['form'].errors.keys())

        # must submit a definition at this step. With the right workgroup
        step_4_data.update({
            'find_de_results-workgroup':self.wg1.pk
            })
        response = self.client.post(self.wizard_url, step_4_data)
        self.assertEqual(response.status_code, 200)
        wizard = response.context['wizard']
        self.assertEqual(wizard['steps'].current, 'completed')

        # Now we save the whole thing
        step_5_data = {}
        step_5_data.update(step_4_data)
        step_5_data.update({
            self.wizard_form_name+'-current_step': 'completed',
        })

        response = self.client.post(self.wizard_url, step_5_data)
        wizard = response.context['wizard']
        self.assertTrue('make_items' in wizard['form'].errors.keys())
        self.assertFalse(models.DataElementConcept.objects.filter(name="Animagus--Animal type").exists())
        self.assertFalse(models.DataElement.objects.filter(name="Animagus--Animal type, MoM Code").exists())
        step_5_data.update({
            'completed-make_items':True
            })
        response = self.client.post(self.wizard_url, step_5_data)
        item = models.DataElement.objects.filter(name="Animagus--Animal type, MoM Code").first()
        self.assertRedirects(response,url_slugify_concept(item))

        self.assertTrue(models.DataElementConcept.objects.filter(name="Animagus--Animal type").exists())
        self.assertTrue(models.DataElement.objects.filter(name="Animagus--Animal type, MoM Code").exists())

"""
    def test_editor_can_make_object__no_prior_components(self):
        self.login_editor()
        step_1_data = {
            self.wizard_form_name+'-current_step': 'component_search',
        }

        response = self.client.post(self.wizard_url, step_1_data)
        wizard = response.context['wizard']
        self.assertEqual(wizard['steps'].current, 'component_search')
        self.assertTrue('oc_name' in wizard['form'].errors.keys())
        self.assertTrue('pr_name' in wizard['form'].errors.keys())

        # must submit a name
        step_1_data.update({'component_search-oc_name':"Animagus"})
        step_1_data.update({'component_search-pr_name':"Animal type"})
        # success!

        response = self.client.post(self.wizard_url, step_1_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wizard['steps'].current, 'component_results')
        self.assertContains(response,"No matching object classes were found")
        self.assertContains(response,"No matching properties were found")

        step_2_data = {
            self.wizard_form_name+'-current_step': 'component_results',
        } # nothing else needed, as we aren't picking a component.

        response = self.client.post(self.wizard_url, step_2_data)
        wizard = response.context['wizard']
        self.assertEqual(wizard['steps'].current, 'make_oc')

        # Now we make the object class
        step_3_data = {
            self.wizard_form_name+'-current_step': 'make_oc',
            'make_oc-name':"Animagus",
        }

        response = self.client.post(self.wizard_url, step_3_data)
        wizard = response.context['wizard']
        self.assertTrue('definition' in wizard['form'].errors.keys())
        self.assertTrue('workgroup' in wizard['form'].errors.keys())

        # no "test item" yet.
        self.assertFalse(models._concept.objects.filter(name="Test Item").exists())

        # must submit a definition at this step. But we are using a non-permitted workgroup.
        step_3_data.update({
            'make_oc-definition':"A wizard who can change shape.",
            'make_oc-workgroup':self.wg2.pk
            })
        response = self.client.post(self.wizard_url, step_3_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertTrue('workgroup' in wizard['form'].errors.keys())

        # must submit a definition at this step. With the right workgroup
        step_3_data.update({
            'make_oc-workgroup':self.wg1.pk
            })
        response = self.client.post(self.wizard_url, step_3_data)
        self.assertEqual(response.status_code, 200)
        wizard = response.context['wizard']
        self.assertEqual(wizard['steps'].current, 'make_p')

        # Now we make the property
        step_4_data = {
            self.wizard_form_name+'-current_step': 'make_p',
            'make_p-name':"Animal type",
        }

        response = self.client.post(self.wizard_url, step_4_data)
        wizard = response.context['wizard']
        self.assertTrue('definition' in wizard['form'].errors.keys())
        self.assertTrue('workgroup' in wizard['form'].errors.keys())

        # no "test item" yet.
        self.assertFalse(models._concept.objects.filter(name="Test Item").exists())

        # must submit a definition at this step. But we are using a non-permitted workgroup.
        step_4_data.update({
            'make_p-definition':"A wizard who can change shape.",
            'make_p-workgroup':self.wg2.pk
            })
        response = self.client.post(self.wizard_url, step_4_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertTrue('workgroup' in wizard['form'].errors.keys())

        # must submit a definition at this step. With the right workgroup
        step_4_data.update({
            'make_p-workgroup':self.wg1.pk
            })
        response = self.client.post(self.wizard_url, step_4_data)
        self.assertEqual(response.status_code, 200)
        wizard = response.context['wizard']
        self.assertEqual(wizard['steps'].current, 'find_dec_results')

        step_4_data.update(step_1_data)
        step_4_data.update(step_2_data)
        step_4_data.update(step_3_data)
        self.assertEqual(response.status_code, 200)
        wizard = response.context['wizard']
        self.assertEqual(response.context['form'].initial['name'], 'Animagus--Animal type')


        step_5_data = {}
        step_5_data.update(step_1_data)
        step_5_data.update(step_2_data)
        step_5_data.update(step_3_data)
        step_5_data.update(step_4_data)
        step_5_data.update({self.wizard_form_name+'-current_step': 'find_dec_results',})

        response = self.client.post(self.wizard_url, step_5_data)
        wizard = response.context['wizard']
        self.assertEqual(response.status_code, 200)
        self.assertTrue('name' in wizard['form'].errors.keys())
"""

"""Ordinary. Wizarding. Level. Examinations. O.W.L.s. More commonly known as 'Owls'.
Study hard and you will be rewarded.
Fail to do so and the consequences may be... severe"""
