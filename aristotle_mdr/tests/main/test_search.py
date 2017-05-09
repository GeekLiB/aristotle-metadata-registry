from django.test import TestCase

import aristotle_mdr.models as models
import aristotle_mdr.perms as perms
import aristotle_mdr.tests.utils as utils
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test.utils import override_settings

from django.test.utils import setup_test_environment
from reversion import revisions as reversion
setup_test_environment()

from time import sleep
import datetime
from django.utils import timezone


class TestSearch(utils.LoggedInViewPages,TestCase):
    def tearDown(self):
        call_command('clear_index', interactive=False, verbosity=0)

    @reversion.create_revision()
    def setUp(self):
        super(TestSearch, self).setUp()
        import haystack
        haystack.connections.reload('default')

        self.ra = models.RegistrationAuthority.objects.create(name="Kelly Act")
        self.ra1 = models.RegistrationAuthority.objects.create(name="Superhuman Registration Act") # Anti-registration!
        self.registrar = User.objects.create_user('stryker','william.styker@weaponx.mil','mutantsMustDie')
        self.ra.giveRoleToUser('registrar',self.registrar)
        self.assertTrue(perms.user_is_registrar(self.registrar,self.ra))
        xmen = "professorX cyclops iceman angel beast phoenix wolverine storm nightcrawler"

        self.xmen_wg = models.Workgroup.objects.create(name="X Men")
        # self.xmen_wg.registrationAuthorities.add(self.ra)
        self.xmen_wg.save()

        self.item_xmen = [
            models.ObjectClass.objects.create(name=t,definition="known xman",workgroup=self.xmen_wg)\
            for t in xmen.split()]
        for item in self.item_xmen:
            registered = self.ra.register(item,models.STATES.standard,self.su)
            self.assertTrue(item in registered['success'])
            item = models._concept.objects.get(pk=item.pk).item # Stupid cache
            self.assertTrue(item.is_public())


        avengers = "thor spiderman ironman hulk captainAmerica"

        self.avengers_wg = models.Workgroup.objects.create(name="Avengers")
        # self.avengers_wg.registrationAuthorities.add(self.ra1)
        self.item_avengers = [
            models.ObjectClass.objects.create(name=t,workgroup=self.avengers_wg)
            for t in avengers.split()]

    def test_search_factory_fails_with_bad_queryset(self):
        from haystack.query import SearchQuerySet
        from haystack.views import search_view_factory
        from django.core.exceptions import ImproperlyConfigured
        from aristotle_mdr.views.views import PermissionSearchView
        from aristotle_mdr.forms.search import PermissionSearchForm
        
        with self.assertRaises(ImproperlyConfigured):
            response = self.client.get(reverse('fail_search')+"?q=wolverine")

    def test_empty_search_loads(self):
        self.logout()
        response = self.client.get(reverse('aristotle:search'))
        self.assertTrue(response.status_code == 200)

    def test_one_result_search_doesnt_have__did_you_mean(self):
        self.logout()
        response = self.client.get(reverse('aristotle:search')+"?q=wolverine")
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['page'].object_list),1)
        self.assertNotContains(response, "Did you mean")
        self.assertContains(response, "wolverine")

    def test_empty_search(self):
        self.logout()
        response = self.client.get(reverse('aristotle:search')+"?q=")
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['page'].object_list),0)

    def test_search_delete_signal(self):
        self.login_superuser()
        with reversion.create_revision():
            cable = models.ObjectClass.objects.create(name="cable",definition="known xman",workgroup=self.xmen_wg)
            self.ra.register(cable,models.STATES.standard,self.su)
            cable.save()
        self.assertTrue(cable.is_public())
        response = self.client.get(reverse('aristotle:search')+"?q=cable")
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['page'].object_list),1)
        with reversion.create_revision():
            cable.delete()
        response = self.client.get(reverse('aristotle:search')+"?q=cable")
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['page'].object_list),0)

    def test_public_search(self):
        self.logout()
        response = self.client.get(reverse('aristotle:search')+"?q=xman")
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['page'].object_list),len(self.item_xmen))
        for i in response.context['page'].object_list:
            self.assertTrue(i.object.is_public())

    def test_public_search_has_valid_facets(self):
        self.logout()
        response = self.client.get(reverse('aristotle:search')+"?q=xman")
        self.assertEqual(response.status_code,200)
        facets = response.context['form'].facets['fields']
        self.assertTrue('workgroup' not in facets.keys())
        self.assertTrue('restriction' not in facets.keys())

        self.assertTrue('facet_model_ct' in facets.keys())
        self.assertTrue('statuses' in facets.keys())
        
        for state, count in facets['statuses']:
            self.assertTrue(int(state) >= self.ra.public_state)

    def test_registrar_search_has_valid_facets(self):
        response = self.client.post(reverse('friendly_login'),
                    {'username': 'stryker', 'password': 'mutantsMustDie'})

        self.assertEqual(response.status_code,302) # logged in

        response = self.client.get(reverse('aristotle:search')+"?q=xman")
        self.assertEqual(response.status_code,200)
        facets = response.context['form'].facets['fields']
        self.assertTrue('workgroup' in facets.keys())
        self.assertTrue('restriction' in facets.keys())

        self.assertTrue('facet_model_ct' in facets.keys())
        self.assertTrue('statuses' in facets.keys())

    def test_registrar_favourite_in_list(self):
        self.logout()
        
        response = self.client.get(reverse('aristotle:search')+"?q=xman")
        self.assertNotContains(response, 'Add Favourite')
        
        response = self.client.post(reverse('friendly_login'),
                    {'username': 'stryker', 'password': 'mutantsMustDie'})

        self.assertEqual(response.status_code,302) # logged in

        response = self.client.get(reverse('aristotle:search')+"?q=xman")
        self.assertNotContains(response, 'This item is in your favourites list')

        i = self.xmen_wg.items.first()
        
        self.registrar.profile.favourites.add(i)
        self.assertTrue(i in self.registrar.profile.favourites.all())
        
        response = self.client.get(reverse('aristotle:search')+"?q=xman")
        self.assertContains(response, 'This item is in your favourites list')

    def test_registrar_search_after_adding_new_status_request(self):
        self.logout()
        response = self.client.post(reverse('friendly_login'),
                    {'username': 'stryker', 'password': 'mutantsMustDie'})

        steve_rogers = models.ObjectClass.objects.get(name="captainAmerica")
        self.assertFalse(perms.user_can_view(self.registrar,steve_rogers))
        review = models.ReviewRequest.objects.create(
            requester=self.su,registration_authority=self.ra,
            state=self.ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )
        review.concepts.add(steve_rogers)

        with reversion.create_revision():
            steve_rogers.save()

        review = models.ReviewRequest.objects.create(
            requester=self.su,registration_authority=self.ra,
            state=self.ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )
        review.concepts.add(steve_rogers)

        self.assertTrue(perms.user_can_view(self.registrar,steve_rogers))

        response = self.client.get(reverse('aristotle:search')+"?q=captainAmerica")
        self.assertEqual(len(response.context['page'].object_list),1)
        self.assertEqual(response.context['page'].object_list[0].object.item,steve_rogers)
        self.assertTrue(perms.user_can_view(self.registrar,response.context['page'].object_list[0].object))

    def test_workgroup_member_search(self):
        self.logout()
        self.viewer = User.objects.create_user('charles.xavier','charles@schoolforgiftedyoungsters.edu','equalRightsForAll')
        self.weaponx_wg = models.Workgroup.objects.create(name="WeaponX")

        response = self.client.post(reverse('friendly_login'),
                    {'username': 'charles.xavier', 'password': 'equalRightsForAll'})

        self.assertEqual(response.status_code,302) # logged in

        #Charles is not in any workgroups
        self.assertFalse(perms.user_in_workgroup(self.viewer,self.xmen_wg))
        self.assertFalse(perms.user_in_workgroup(self.viewer,self.weaponx_wg))

        #Create Deadpool in Weapon X workgroup
        with reversion.create_revision():
            dp = models.ObjectClass.objects.create(name="deadpool",
                    definition="not really an xman, no matter how much he tries",
                    workgroup=self.weaponx_wg)
        dp = models.ObjectClass.objects.get(pk=dp.pk) # Un-cache
        self.assertFalse(perms.user_can_view(self.viewer,dp))
        self.assertFalse(dp.is_public())

        # Charles isn't a viewer of X-men yet, so no results.
        from aristotle_mdr.forms.search import PermissionSearchQuerySet
        psqs = PermissionSearchQuerySet()
        psqs = psqs.auto_query('deadpool').apply_permission_checks(self.viewer)
        self.assertEqual(len(psqs),0)
        #response = self.client.get(reverse('aristotle:search')+"?q=deadpool")
        #self.assertEqual(len(response.context['page'].object_list),0)

        # Make viewer of XMen
        self.xmen_wg.giveRoleToUser('viewer',self.viewer)
        self.assertFalse(perms.user_can_view(self.viewer,dp))

        # Deadpool isn't an Xman yet, still no results.
        psqs = PermissionSearchQuerySet()
        psqs = psqs.auto_query('deadpool').apply_permission_checks(self.viewer)
        self.assertDelayedEqual(len(psqs),0)

        with reversion.create_revision():
            dp.workgroup = self.xmen_wg
            dp.save()
        dp = models.ObjectClass.objects.get(pk=dp.pk) # Un-cache

        # Charles is a viewer, Deadpool is in X-men, should have results now.
        psqs = PermissionSearchQuerySet()
        psqs = psqs.auto_query('deadpool').apply_permission_checks(self.viewer)
        self.assertDelayedEqual(len(psqs),1)

        response = self.client.get(reverse('aristotle:search')+"?q=deadpool")
        self.assertTrue(perms.user_can_view(self.viewer,dp))
        self.assertDelayedEqual(len(response.context['page'].object_list),1)
        self.assertEqual(response.context['page'].object_list[0].object.item,dp)

        # Take away Charles viewing rights and no results again.
        self.xmen_wg.removeRoleFromUser('viewer',self.viewer)
        psqs = PermissionSearchQuerySet()
        psqs = psqs.auto_query('deadpool').apply_permission_checks(self.viewer)
        self.assertDelayedEqual(len(psqs),0)

        response = self.client.get(reverse('aristotle:search')+"?q=deadpool")
        self.assertDelayedEqual(len(response.context['page'].object_list),0)

    def test_workgroup_member_search_has_valid_facets(self):
        self.logout()
        self.viewer = User.objects.create_user('charles.xavier','charles@schoolforgiftedyoungsters.edu','equalRightsForAll')
        response = self.client.post(reverse('friendly_login'),
                    {'username': 'charles.xavier', 'password': 'equalRightsForAll'})

        self.assertEqual(response.status_code,302) # logged in

        self.xmen_wg.giveRoleToUser('viewer',self.viewer)
        self.weaponx_wg = models.Workgroup.objects.create(name="WeaponX")

        response = self.client.post(reverse('friendly_login'),
                    {'username': 'charles.xavier', 'password': 'equalRightsForAll'})

        self.assertEqual(response.status_code,302) # logged in

        #Create Deadpool in Weapon X workgroup
        with reversion.create_revision():
            dp = models.ObjectClass.objects.create(name="deadpool",
                    definition="not really an xman, no matter how much he tries",
                    workgroup=self.weaponx_wg)
        dp = models.ObjectClass.objects.get(pk=dp.pk) # Un-cache
        self.assertFalse(perms.user_can_view(self.viewer,dp))
        self.assertFalse(dp.is_public())

        response = self.client.get(reverse('aristotle:search')+"?q=xman")
        self.assertEqual(response.status_code,200)
        facets = response.context['form'].facets['fields']
        self.assertTrue('restriction' in facets.keys())

        self.assertTrue('facet_model_ct' in facets.keys())
        self.assertTrue('statuses' in facets.keys())
        self.assertTrue('workgroup' in facets.keys())

        for wg, count in facets['workgroup']:
            wg = models.Workgroup.objects.get(pk=wg)
            self.assertTrue(perms.user_in_workgroup(self.viewer,wg))

    def test_current_statuses_only_in_search_results_and_index(self):
        # See issue #327
        self.logout()
        response = self.client.post(reverse('friendly_login'),
                    {'username': 'stryker', 'password': 'mutantsMustDie'})

        self.assertEqual(response.status_code,302) # logged in
        self.assertTrue(perms.user_is_registrar(self.registrar,self.ra))

        with reversion.create_revision():
            dp = models.ObjectClass.objects.create(name="deadpool",
                    definition="not really an xman, no matter how much he tries",
                    workgroup=self.xmen_wg)

        review = models.ReviewRequest.objects.create(
            requester=self.su,registration_authority=self.ra,
            state=self.ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )
        review.concepts.add(dp)

        dp = models.ObjectClass.objects.get(pk=dp.pk) # Un-cache
        self.assertTrue(perms.user_can_view(self.registrar,dp))
        self.assertFalse(dp.is_public())

        self.ra.register(dp,models.STATES.incomplete,self.registrar,
            registrationDate=timezone.now()+datetime.timedelta(days=-7)
        )

        self.ra.register(dp,models.STATES.standard,self.registrar,
            registrationDate=timezone.now()+datetime.timedelta(days=-1)
        )

        response = self.client.get(reverse('aristotle:search')+"?q=deadpool")
        self.assertEqual(len(response.context['page'].object_list),1)
        dp_result = response.context['page'].object_list[0]
        self.assertTrue(dp_result.object.name=="deadpool")
        self.assertTrue(len(dp_result.statuses) == 1)

        self.assertTrue(int(dp_result.statuses[0]) == int(models.STATES.standard))

    def test_visibility_restriction_facets(self):
        # See issue #351
        self.logout()
        
        response = self.client.get(reverse('aristotle:search')+"?q=xman")
        self.assertNotContains(response, 'Restriction')

        response = self.client.post(reverse('friendly_login'),
                    {'username': 'stryker', 'password': 'mutantsMustDie'})

        self.assertEqual(response.status_code,302) # logged in
        self.assertTrue(perms.user_is_registrar(self.registrar,self.ra))

        with reversion.create_revision():
            dp = models.ObjectClass.objects.create(name="deadpool",
                    definition="not really an xman, no matter how much he tries",
                    workgroup=self.xmen_wg)

        review = models.ReviewRequest.objects.create(
            requester=self.su,registration_authority=self.ra,
            state=self.ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )
        review.concepts.add(dp)

        dp = models.ObjectClass.objects.get(pk=dp.pk) # Un-cache
        self.assertTrue(perms.user_can_view(self.registrar,dp))
        self.assertFalse(dp.is_public())

        self.ra.register(dp,models.STATES.candidate,self.registrar,
            registrationDate=timezone.now()+datetime.timedelta(days=-7)
        )

        response = self.client.get(reverse('aristotle:search')+"?q=xman")
        self.assertContains(response, 'Restriction')
        

        response = self.client.get(reverse('aristotle:search')+"?q=xman&res=1")
        self.assertNotContains(response, 'Restriction')

        self.assertContains(response, 'Item visibility state is Locked')

        self.assertEqual(len(response.context['page'].object_list),1)
        dp_result = response.context['page'].object_list[0]
        self.assertTrue(dp_result.object.name=="deadpool")
        self.assertTrue(len(dp_result.statuses) == 1)
        self.assertTrue(dp_result.object.is_locked())
        self.assertFalse(dp_result.object.is_public())

        self.assertTrue(int(dp_result.statuses[0]) == int(models.STATES.candidate))

    def test_user_can_search_own_content(self):
        self.logout()
        self.login_regular_user()
        response = self.client.get(reverse('aristotle:search')+"?q=pokemon")
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['page'].object_list),0)
        
        url = reverse('aristotle:createItem', args=['aristotle_mdr', 'objectclass'])
        
        step_1_data = {
            'dynamic_aristotle_wizard-current_step': 'initial',
            'initial-name':"pokemon",
        }

        response = self.client.post(url, step_1_data)
        response = self.client.post(url, {
            'dynamic_aristotle_wizard-current_step': 'results',
            'results-name':"pokemon",
            'results-definition':"Test Definition",
            'results-workgroup':""
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(models.ObjectClass.objects.filter(name="pokemon").exists())

        response = self.client.get(reverse('aristotle:search')+"?q=pokemon")
        self.assertEqual(response.status_code,200)
        self.assertDelayedEqual(len(response.context['page'].object_list),1)

        self.logout()
        self.login_editor()
        response = self.client.get(reverse('aristotle:search')+"?q=pokemon")
        self.assertEqual(response.status_code,200)
        self.assertDelayedEqual(len(response.context['page'].object_list),0)


    def test_user_can_search_own_content_and_other_content(self):
        self.logout()
        self.login_regular_user()
        response = self.client.get(reverse('aristotle:search')+"?q=pokemon")
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['page'].object_list),0)
        
        url = reverse('aristotle:createItem', args=['aristotle_mdr', 'objectclass'])
        
        step_1_data = {
            'dynamic_aristotle_wizard-current_step': 'initial',
            'initial-name':"pokemon",
        }

        response = self.client.post(url, step_1_data)
        response = self.client.post(url, {
            'dynamic_aristotle_wizard-current_step': 'results',
            'results-name':"pokemon",
            'results-definition':"Test Definition",
            'results-workgroup':""
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(models.ObjectClass.objects.filter(name="pokemon").exists())

        response = self.client.get(reverse('aristotle:search')+"?q=pokemon")
        self.assertEqual(response.status_code,200)
        self.assertDelayedEqual(len(response.context['page'].object_list),1)

        self.logout()
        self.login_editor()
        response = self.client.get(reverse('aristotle:search')+"?q=pokemon")
        self.assertEqual(response.status_code,200)
        self.assertDelayedEqual(len(response.context['page'].object_list),0)

        # Get item
        item = models.ObjectClass.objects.get(name='pokemon')
        self.ra.register(item, models.STATES.standard, self.su)

        response = self.client.get(reverse('aristotle:search')+"?q=pokemon")
        self.assertEqual(response.status_code,200)
        self.assertDelayedEqual(len(response.context['page'].object_list),1)


    def test_facet_search(self):
        self.logout()

        with reversion.create_revision():
            oc = models.ObjectClass.objects.create(
                name="Pokemon",
                definition="a Pocket monster"
            )
            dec = models.DataElementConcept.objects.create(
                name="Pokemon-CombatPower",
                definition="a Pokemons combat power",
                objectClass=oc
            )
            de = models.DataElement.objects.create(
                name="Pokemon-Combat Power, Go",
                definition="a Pokemons combat power as recorded in the Pokemon-Go scale",
                dataElementConcept=dec
            )

        self.login_superuser()

        from aristotle_mdr.forms.search import PermissionSearchQuerySet
        response = self.client.get(reverse('aristotle:search')+"?q=pokemon")
        
        objs = response.context['page'].object_list
        self.assertDelayedEqual(len(objs),3)
        extra_facets = response.context['form'].extra_facet_fields

        self.assertTrue(len(extra_facets) == 2)
        self.assertTrue('data_element_concept' in [f[0] for f in extra_facets] )
        self.assertTrue('object_class' in [f[0] for f in extra_facets] )
        
        # Confirm spaces are included in the facet
        self.assertTrue(dec.name in [v[0] for v in dict(extra_facets)['data_element_concept']['values']])

        psqs = PermissionSearchQuerySet()
        psqs = psqs.auto_query('pokemon').apply_permission_checks(self.su)
        self.assertDelayedEqual(len(psqs),3)

        response = self.client.get(reverse('aristotle:search')+"?q=pokemon")
        objs = response.context['page'].object_list
        self.assertDelayedEqual(len(objs),3)

        response = self.client.get(reverse('aristotle:search')+"?q=pokemon&f=object_class::%s"%oc.name)

        objs = response.context['page'].object_list
        self.assertDelayedEqual(len(objs),2)
        self.assertTrue(de.pk in [o.object.pk for o in objs])
        self.assertTrue(dec.pk in [o.object.pk for o in objs])

        response = self.client.get(reverse('aristotle:search')+"?q=pokemon&f=data_element_concept::%s"%dec.name.replace(' ','+'))

        objs = response.context['page'].object_list
        self.assertDelayedEqual(len(objs),2)
        self.assertTrue(de.pk in [o.object.pk for o in objs])
        self.assertTrue(dec.pk in [o.object.pk for o in objs])

        response = self.client.get(reverse('aristotle:search')+"?q=pokemon&models=aristotle_mdr.dataelement&f=data_element_concept::%s"%dec.name.replace(' ','+'))

        objs = response.context['page'].object_list
        self.assertDelayedEqual(len(objs),1)
        self.assertTrue(de.pk in [o.object.pk for o in objs])
        self.assertTrue(dec.pk not in [o.object.pk for o in objs])

    def test_model_search(self):
        self.logout()

        with reversion.create_revision():
            dec = models.DataElementConcept.objects.create(
                name="Pokemon-CP",
                definition="a Pokemons combat power"
            )
            de = models.DataElement.objects.create(
                name="Pokemon-CP, Go",
                definition="a Pokemons combat power as recorded in the Pokemon-Go scale",
                dataElementConcept=dec
            )

        self.login_superuser()

        from aristotle_mdr.forms.search import PermissionSearchQuerySet
        response = self.client.get(reverse('aristotle:search')+"?q=pokemon")
        
        objs = response.context['page'].object_list
        self.assertDelayedEqual(len(objs),2)

        response = self.client.get(reverse('aristotle:search')+"?q=pokemon&models=aristotle_mdr.dataelement")

        objs = response.context['page'].object_list
        self.assertDelayedEqual(len(objs),1)
        self.assertTrue(objs[0].object.pk,de.pk)


class TestTokenSearch(TestCase):
    def tearDown(self):
        call_command('clear_index', interactive=False, verbosity=0)

    @reversion.create_revision()
    def setUp(self):
        # These are really terrible Object Classes, but I was bored and needed to spice things up.
        # Technically, the Object Class would be "Mutant"
        super(TestTokenSearch, self).setUp()
        import haystack
        haystack.connections.reload('default')

        self.su = User.objects.create_superuser('super','','user')

        self.ra = models.RegistrationAuthority.objects.create(name="Kelly Act")
        self.registrar = User.objects.create_user('stryker','william.styker@weaponx.mil','mutantsMustDie')
        self.ra.giveRoleToUser('registrar',self.registrar)
        xmen = "wolverine professorX cyclops iceman angel beast phoenix storm nightcrawler"
        self.xmen_wg = models.Workgroup.objects.create(name="X Men")
        self.xmen_wg.save()

        self.item_xmen = [
            models.ObjectClass.objects.create(name=t,version="0.%d.0"%(v+1),definition="known x-man",workgroup=self.xmen_wg)
            for v,t in enumerate(xmen.split())]
        self.item_xmen.append(
            models.Property.objects.create(name="Power",definition="What power a mutant has?",workgroup=self.xmen_wg)
            )

        for item in self.item_xmen:
            self.ra.register(item,models.STATES.standard,self.su)

    def test_token_version_search(self):
        self.assertEqual(models.ObjectClass.objects.get(version='0.1.0').name,"wolverine")

        response = self.client.get(reverse('aristotle:search')+"?q=version:0.1.0")
        self.assertEqual(response.status_code,200)
        objs = response.context['page'].object_list
        self.assertEqual(len(objs),1)
        self.assertTrue(objs[0].object.name,"wolverine")

    def test_token_type_search(self):
        response = self.client.get(reverse('aristotle:search')+"?q=type:property")
        self.assertEqual(response.status_code,200)
        objs = response.context['page'].object_list
        self.assertEqual(len(objs),1)
        self.assertTrue(objs[0].object.name,"Power")

        response = self.client.get(reverse('aristotle:search')+"?q=type:p")
        self.assertEqual(response.status_code,200)
        objs = response.context['page'].object_list
        self.assertEqual(len(objs),1)
        self.assertTrue(objs[0].object.name,"Power")


class TestSearchDescriptions(TestCase):
    """
    Test the 'form to plain text' description generator
    """
    # def setUp(self):
    
    def test_descriptions(self):
        from aristotle_mdr.forms.search import PermissionSearchForm as PSF
        from aristotle_mdr.templatetags.aristotle_search_tags import \
            search_describe_filters as gen

        ra = models.RegistrationAuthority.objects.create(name='Filter RA')

        filters = {'models':['aristotle_mdr.objectclass']}
        form = PSF(filters)
        
        if not form.is_valid(): # pragma: no cover
            # If this branch happens, we messed up the test bad.
            print(form.errors)
            self.assertTrue('programmer' is 'good')

        description = gen(form)
        self.assertTrue('Item type is Object Classes' == description)
        self.assertTrue('and' not in description)

        filters = {'models':[
            'aristotle_mdr.objectclass',
            'aristotle_mdr.property',
            'aristotle_mdr.dataelement',
        ]}
        form = PSF(filters)
        if not form.is_valid(): # pragma: no cover
            print(form.errors)
            self.assertTrue('programmer' is 'good')
        
        description = gen(form)

        self.assertTrue(
            'item type is object classes, properties or data elements' == description.lower()
        )
        self.assertTrue('and' not in description)

        filters = {'models':['aristotle_mdr.objectclass'],'ra':[str(ra.pk)]}
        form = PSF(filters)
        if not form.is_valid(): # pragma: no cover
            print(form.errors)
            self.assertTrue('programmer' is 'good')

        description = gen(form)

        self.assertTrue('Item type is Object Classes' in gen(form))
        self.assertTrue('registration authority is %s'%ra.name.lower() in gen(form).lower())
        self.assertTrue('and' in description)

        filters = {
            'models':['aristotle_mdr.objectclass'],
            'res':0
        }
        form = PSF(filters)
        
        if not form.is_valid(): # pragma: no cover
            # If this branch happens, we messed up the test bad.
            print(form.errors)
            self.assertTrue('programmer' is 'good')

        description = gen(form)
        self.assertTrue('Item type is Object Classes' in description)
        self.assertTrue('and' in description)
        self.assertTrue('Item visibility state is Public' in description)
