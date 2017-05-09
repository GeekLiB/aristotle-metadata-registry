from django.contrib.admin import helpers
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.forms import model_to_dict
from django.test import TestCase
from django.test.utils import setup_test_environment

import datetime

import aristotle_mdr.models as models
import aristotle_mdr.perms as perms
import aristotle_mdr.tests.utils as utils

setup_test_environment()

class AdminPage(utils.LoggedInViewPages,TestCase):
    def setUp(self):
        super(AdminPage, self).setUp()

    def test_workgroup_list(self):
        new_editor = User.objects.create_user('new_eddie','','editor')
        new_editor.is_staff=True
        new_editor.save()

        wg_nm = models.Workgroup.objects.create(name="normal and is manager")
        wg_am = models.Workgroup.objects.create(name="archived and is manager",archived=True)
        wg_nv = models.Workgroup.objects.create(name="normal and is viewer")
        wg_av = models.Workgroup.objects.create(name="archived and is viewer",archived=True)
        wg_ns = models.Workgroup.objects.create(name="normal and is submitter")
        wg_as = models.Workgroup.objects.create(name="archived and is submitter",archived=True)
        wg_nw = models.Workgroup.objects.create(name="normal and is steward")
        wg_aw = models.Workgroup.objects.create(name="archived and is steward",archived=True)

        wg_nm.managers.add(new_editor)
        wg_am.managers.add(new_editor)
        wg_nv.viewers.add(new_editor)
        wg_av.viewers.add(new_editor)
        wg_ns.submitters.add(new_editor)
        wg_as.submitters.add(new_editor)
        wg_nw.stewards.add(new_editor)
        wg_aw.stewards.add(new_editor)

        new_editor = User.objects.get(pk=new_editor.pk) # decache

        self.assertEqual(new_editor.profile.editable_workgroups.count(),2)
        self.assertTrue(wg_ns in new_editor.profile.editable_workgroups.all())
        self.assertTrue(wg_nw in new_editor.profile.editable_workgroups.all())

        self.logout()
        response = self.client.post(reverse('friendly_login'), {'username': 'new_eddie', 'password': 'editor'})
        self.assertEqual(response.status_code,302)

        t = models.ObjectClass
        response = self.client.get(reverse("admin:%s_%s_add"%(t._meta.app_label,t._meta.model_name)))
        self.assertEqual(response.context['adminform'].form.fields['workgroup'].queryset.count(),2)
        self.assertTrue(wg_ns in response.context['adminform'].form.fields['workgroup'].queryset.all())
        self.assertTrue(wg_nw in response.context['adminform'].form.fields['workgroup'].queryset.all())

    def test_clone(self):
        from aristotle_mdr.utils import concept_to_clone_dict

        # Does cloning an item prepopulate everythin?
        self.login_editor()
        oc = models.ObjectClass.objects.create(name="OC1",workgroup=self.wg1)
        prop = models.Property.objects.create(name="Prop1",workgroup=self.wg1)
        dec = models.DataElementConcept.objects.create(name="DEC1",objectClass=oc,property=prop,workgroup=self.wg1)

        response = self.client.get(reverse("admin:aristotle_mdr_dataelementconcept_add")+"?clone=%s"%dec.id)
        self.assertResponseStatusCodeEqual(response,200)
        self.assertEqual(response.context['adminform'].form.initial,concept_to_clone_dict(dec))

    def test_name_suggests(self):
        self.login_editor()
        oc = models.ObjectClass.objects.create(name="OC1",workgroup=self.wg1)
        prop = models.Property.objects.create(name="Prop1",workgroup=self.wg1)
        dec = models.DataElementConcept.objects.create(name="DEC1",objectClass=oc,property=prop,workgroup=self.wg1)

        response = self.client.get(reverse("admin:aristotle_mdr_dataelementconcept_change",args=[dec.pk]))
        self.assertResponseStatusCodeEqual(response,200)

    def test_su_can_view_users_list(self):
        self.login_superuser()
        response = self.client.get(
            reverse('admin:%s_%s_changelist' % ('auth','user')),
        )
        self.assertContains(response,'Last login')

    def test_su_can_add_new_user(self):
        self.login_superuser()
        response = self.client.post(
            reverse("admin:auth_user_add"),
            {
                'username':"newuser",'password1':"test",'password2':"test",
                'profile-TOTAL_FORMS': 1, 'profile-INITIAL_FORMS': 0, 'profile-MAX_NUM_FORMS': 1,
                'profile-0-workgroup_manager_in': [self.wg1.id],
                'profile-0-steward_in': [self.wg1.id],
                'profile-0-submitter_in': [self.wg1.id],
                'profile-0-viewer_in': [self.wg1.id],
                'profile-0-organization_manager_in': [self.ra.id],
                'profile-0-registrar_in': [self.ra.id],

            }
        )
        self.assertResponseStatusCodeEqual(response,302)
        new_user = User.objects.get(username='newuser')
        self.assertEqual(new_user.profile.workgroups.count(),1)
        self.assertEqual(new_user.profile.workgroups.first(),self.wg1)
        self.assertEqual(new_user.profile.registrarAuthorities.count(),1)
        self.assertEqual(new_user.profile.registrarAuthorities.first(),self.ra)
        for rel in [new_user.workgroup_manager_in,
                    new_user.steward_in,
                    new_user.submitter_in,
                    new_user.viewer_in]:
            self.assertEqual(rel.count(),1)
            self.assertEqual(rel.first(),self.wg1)

        self.assertEqual(new_user.organization_manager_in.count(),1)
        self.assertEqual(new_user.organization_manager_in.first(),self.ra.organization_ptr)

        self.assertEqual(new_user.registrar_in.count(),1)
        self.assertEqual(new_user.registrar_in.first(),self.ra)

        response = self.client.post(
            reverse("admin:auth_user_add"),
            {
                'username':"newuser_with_none",'password1':"test",'password2':"test",
                'profile-TOTAL_FORMS': 1, 'profile-INITIAL_FORMS': 0, 'profile-MAX_NUM_FORMS': 1,
            }
        )
        self.assertResponseStatusCodeEqual(response,302)
        new_user = User.objects.get(username='newuser_with_none')
        self.assertEqual(new_user.profile.workgroups.count(),0)
        self.assertEqual(new_user.profile.registrarAuthorities.count(),0)
        for rel in [new_user.workgroup_manager_in,
                    new_user.steward_in,
                    new_user.submitter_in,
                    new_user.viewer_in]:
            self.assertEqual(rel.count(),0)
        for rel in [new_user.organization_manager_in,
                    new_user.registrar_in,]:
            self.assertEqual(rel.count(),0)


    def test_editor_can_view_admin_page(self):
        self.login_editor()
        response = self.client.get(reverse("admin:index"))
        self.assertResponseStatusCodeEqual(response,200)

class AdminPageForConcept(utils.LoggedInViewPages):
    form_defaults = {}
    create_defaults = {}
    def setUp(self,instant_create=True):
        super(AdminPageForConcept, self).setUp()
        if instant_create:
            self.create_items()

    def create_items(self):
        self.item1 = self.itemType.objects.create(name="admin_page_test_oc",definition="my definition",workgroup=self.wg1,**self.create_defaults)

    def test_registration_authority_inline_not_in_editor_admin_page(self):
        self.login_editor()

        response = self.client.get(reverse("admin:%s_%s_change"%(self.itemType._meta.app_label,self.itemType._meta.model_name),args=[self.item1.pk]))
        self.assertResponseStatusCodeEqual(response,200)

        hidden_input='<input type="hidden" id="id_statuses-0-registrationAuthority" name="statuses-0-registrationAuthority" value="%s" />'%(self.ra.pk)
        self.assertNotContainsHtml(response,hidden_input)

        register = self.ra.register(self.item1,models.STATES.incomplete,self.su)
        self.assertEqual(register,{'success':[self.item1],'failed':[]})
        self.assertEqual(self.item1.current_statuses()[0].state,models.STATES.incomplete)

        response = self.client.get(reverse("admin:%s_%s_change"%(self.itemType._meta.app_label,self.itemType._meta.model_name),args=[self.item1.pk]))
        self.assertResponseStatusCodeEqual(response,200)
        self.assertNotContainsHtml(response,hidden_input)

    def test_registration_authority_inline_inactive(self):
        self.login_superuser()

        response = self.client.get(reverse("admin:%s_%s_change"%(self.itemType._meta.app_label,self.itemType._meta.model_name),args=[self.item1.pk]))
        self.assertResponseStatusCodeEqual(response,200)

        hidden_input='<input type="hidden" id="id_statuses-0-registrationAuthority" name="statuses-0-registrationAuthority" value="%s" />'%(self.ra.pk)
        self.assertNotContainsHtml(response,hidden_input)

        register = self.ra.register(self.item1,models.STATES.incomplete,self.su)
        self.assertEqual(register,{'success':[self.item1],'failed':[]})
        self.item1 = self.itemType.objects.get(pk=self.item1.pk) # Stupid cache
        self.assertEqual(self.item1.current_statuses()[0].state,models.STATES.incomplete)

        response = self.client.get(reverse("admin:%s_%s_change"%(self.itemType._meta.app_label,self.itemType._meta.model_name),args=[self.item1.pk]))
        self.assertResponseStatusCodeEqual(response,200)
        self.assertContainsHtml(response,hidden_input)

    def test_editor_make_item(self):
        self.login_editor()

        before_count = self.wg1.items.count()
        response = self.client.get(reverse("admin:%s_%s_changelist"%(self.itemType._meta.app_label,self.itemType._meta.model_name)))
        self.assertResponseStatusCodeEqual(response,200)
        response = self.client.get(reverse("admin:%s_%s_add"%(self.itemType._meta.app_label,self.itemType._meta.model_name)))
        self.assertResponseStatusCodeEqual(response,200)
        # make an item
        response = self.client.get(reverse("admin:%s_%s_add"%(self.itemType._meta.app_label,self.itemType._meta.model_name)))

        data = {'name':"admin_page_test_oc",'definition':"test","workgroup":self.wg1.id,
                    'statuses-TOTAL_FORMS': 0, 'statuses-INITIAL_FORMS': 0 # no substatuses
                }
        data.update(self.form_defaults)

        response = self.client.post(reverse("admin:%s_%s_add"%(self.itemType._meta.app_label,self.itemType._meta.model_name)),data)

        self.assertResponseStatusCodeEqual(response,302)
        self.assertRedirects(response,reverse("admin:%s_%s_changelist"%(self.itemType._meta.app_label,self.itemType._meta.model_name)))
        self.assertEqual(self.wg1.items.first().name,"admin_page_test_oc")
        self.assertEqual(self.wg1.items.count(),before_count+1)

        # Editor can't save in WG2, so this won't redirect.
        data.update({"workgroup":self.wg2.id})
        response = self.client.post(reverse("admin:%s_%s_add"%(self.itemType._meta.app_label,self.itemType._meta.model_name)),data)

        self.assertEqual(self.wg2.items.count(),0)
        self.assertResponseStatusCodeEqual(response,200)

    def test_editor_deleting_allowed_item(self):
        self.login_editor()

        before_count = self.wg1.items.count()
        self.assertEqual(self.wg1.items.count(),1)
        response = self.client.get(reverse("admin:%s_%s_delete"%(self.itemType._meta.app_label,self.itemType._meta.model_name),args=[self.item1.pk]))
        self.assertResponseStatusCodeEqual(response,200)
        response = self.client.post(
            reverse("admin:%s_%s_delete"%(self.itemType._meta.app_label,self.itemType._meta.model_name),args=[self.item1.pk]),
            {'post':'yes'}
            )
        self.assertRedirects(response,reverse("admin:%s_%s_changelist"%(self.itemType._meta.app_label,self.itemType._meta.model_name)))
        self.assertEqual(self.wg1.items.count(),before_count-1)

        self.item1 = self.itemType.objects.create(name="OC1",workgroup=self.wg1, **self.create_defaults)
        self.assertEqual(self.wg1.items.count(),1)
        before_count = self.wg1.items.count()

        review = models.ReviewRequest.objects.create(
            requester=self.su,registration_authority=self.ra,
            state=self.ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )
        review.concepts.add(self.item1)
        old_count = self.item1.statuses.count()
        self.ra.register(self.item1,models.STATES.standard,self.registrar)
        self.assertTrue(self.item1.statuses.count() == old_count + 1)


        self.item1 = self.itemType.objects.get(pk=self.item1.pk) # Dang DB cache
        self.assertTrue(self.item1.is_registered)
        self.assertTrue(self.item1.is_locked())
        self.assertFalse(perms.user_can_edit(self.editor,self.item1))

        before_count = self.wg1.items.count()
        response = self.client.get(reverse("admin:%s_%s_delete"%(self.itemType._meta.app_label,self.itemType._meta.model_name),args=[self.item1.pk]))
        self.assertResponseStatusCodeEqual(response,404)

        self.assertEqual(self.wg1.items.count(),before_count)
        response = self.client.post(
            reverse("admin:%s_%s_delete"%(self.itemType._meta.app_label,self.itemType._meta.model_name),args=[self.item1.pk]),
            {'post':'yes'}
            )
        self.assertResponseStatusCodeEqual(response,404)
        self.assertEqual(self.wg1.items.count(),before_count)

    def test_editor_deleting_forbidden_item(self):
        self.login_editor()
        self.item2 = self.itemType.objects.create(name="OC2",workgroup=self.wg2, **self.create_defaults)

        before_count = self.wg2.items.count()
        response = self.client.get(reverse("admin:%s_%s_delete"%(self.itemType._meta.app_label,self.itemType._meta.model_name),args=[self.item2.pk]))
        self.assertResponseStatusCodeEqual(response,404)
        self.assertEqual(self.wg2.items.count(),before_count)

        before_count = self.wg2.items.count()
        response = self.client.post(
            reverse("admin:%s_%s_delete"%(self.itemType._meta.app_label,self.itemType._meta.model_name),args=[self.item2.pk]),
            {'post':'yes'}
            )
        self.assertResponseStatusCodeEqual(response,404)
        self.assertEqual(self.wg2.items.count(),before_count)

    def test_editor_change_item(self):
        self.login_editor()
        response = self.client.get(reverse("admin:%s_%s_change"%(self.itemType._meta.app_label,self.itemType._meta.model_name),args=[self.item1.pk]))
        self.assertResponseStatusCodeEqual(response,200)

        updated_item = dict((k,v) for (k,v) in model_to_dict(self.item1).items() if v is not None)
        updated_name = updated_item['name'] + " updated!"
        updated_item['name'] = updated_name

        updated_item.update({
            'statuses-TOTAL_FORMS': 0, 'statuses-INITIAL_FORMS': 0 # no statuses
        })
        updated_item.update(self.form_defaults)
        self.assertTrue(self.wg1 in self.editor.profile.editable_workgroups.all())

        self.assertEqual([self.wg1],list(response.context['adminform'].form.fields['workgroup'].queryset))

        self.assertTrue(perms.user_can_edit(self.editor,self.item1))
        self.assertTrue(self.item1.workgroup in self.editor.profile.editable_workgroups.all())
        response = self.client.post(
                reverse("admin:%s_%s_change"%(self.itemType._meta.app_label,self.itemType._meta.model_name),args=[self.item1.id]),
                updated_item
                )

        self.assertResponseStatusCodeEqual(response,302)

        self.item1 = self.itemType.objects.get(pk=self.item1.pk)
        self.assertEqual(self.item1.name,updated_name)

# deprecated
    def test_supersedes_saves(self):
        self.item2 = self.itemType.objects.create(name="admin_page_test_oc_2",definition="my definition",workgroup=self.wg1,**self.create_defaults)
        self.item3 = self.itemType.objects.create(name="admin_page_test_oc_2",definition="my definition",workgroup=self.wg1,**self.create_defaults)

        self.login_editor()
        response = self.client.get(reverse("admin:%s_%s_change"%(self.itemType._meta.app_label,self.itemType._meta.model_name),args=[self.item1.pk]))
        self.assertResponseStatusCodeEqual(response,200)

        updated_item = dict((k,v) for (k,v) in model_to_dict(self.item1).items() if v is not None)
        updated_name = updated_item['name'] + " updated!"
        updated_item['name'] = updated_name

        updated_item.update({
            'statuses-TOTAL_FORMS': 0, 'statuses-INITIAL_FORMS': 0, # no statuses
            'deprecated':[self.item2.id,self.item3.id]
        })
        updated_item.update(self.form_defaults)

        response = self.client.post(
                reverse("admin:%s_%s_change"%(self.itemType._meta.app_label,self.itemType._meta.model_name),args=[self.item1.pk]),
                updated_item
                )
        # Make sure it saves
        self.assertRedirects(response,reverse("admin:%s_%s_changelist"%(self.itemType._meta.app_label,self.itemType._meta.model_name)))

        self.item1 = self.itemType.objects.get(pk=self.item1.pk)
        self.assertTrue(self.item2 in self.item1.supersedes.all().select_subclasses())
        self.assertTrue(self.item3 in self.item1.supersedes.all().select_subclasses())

    def test_superseded_by_saves(self):
        self.item2 = self.itemType.objects.create(name="admin_page_test_oc_2",definition="my definition",workgroup=self.wg1,**self.create_defaults)

        self.login_editor()
        response = self.client.get(reverse("admin:%s_%s_change"%(self.itemType._meta.app_label,self.itemType._meta.model_name),args=[self.item1.pk]))
        self.assertResponseStatusCodeEqual(response,200)

        updated_item = dict((k,v) for (k,v) in model_to_dict(self.item1).items() if v is not None)
        updated_name = updated_item['name'] + " updated!"
        updated_item['name'] = updated_name

        updated_item.update({
            'statuses-TOTAL_FORMS': 0, 'statuses-INITIAL_FORMS': 0, # no statuses
            'superseded_by':self.item2.id
        })
        updated_item.update(self.form_defaults)

        response = self.client.post(
                reverse("admin:%s_%s_change"%(self.itemType._meta.app_label,self.itemType._meta.model_name),args=[self.item1.pk]),
                updated_item
                )

        # Make sure it saves
        self.assertRedirects(response,reverse("admin:%s_%s_changelist"%(self.itemType._meta.app_label,self.itemType._meta.model_name)))

        self.item1 = self.itemType.objects.get(pk=self.item1.pk)
        self.assertTrue(self.item2 == self.item1.superseded_by.item)

    def test_history_page_loads(self):
        self.login_editor()
        response = self.client.get(
            reverse("admin:%s_%s_history"%(self.itemType._meta.app_label,self.itemType._meta.model_name),
            args=[self.item1.pk])
            )
        self.assertResponseStatusCodeEqual(response,200)

    def test_prior_version_page_loads(self):
        # Not going to let this issue crop up again!
        from reversion import revisions as reversion
        new_name = "A different name"
        with reversion.create_revision():
            self.item1.name = new_name
            self.item1.save()
        from reversion.models import Version
        version_list = Version.objects.get_for_object(self.item1)

        self.login_editor()
        response = self.client.get(
            reverse("admin:%s_%s_revision"%(self.itemType._meta.app_label,self.itemType._meta.model_name),
            args=[self.item1.pk,version_list.last().id])
            )
        self.assertResponseStatusCodeEqual(response,200)
        self.assertTrue(response.context['adminform'].form.initial['name'],new_name)

    def test_admin_user_can_compare_statuses(self):
        self.login_editor()

        from reversion import revisions as reversion
        
        with reversion.create_revision():
            self.item1.name = "change 1"
            reversion.set_comment("change 1")
            self.item1.save()

        old_count = self.item1.statuses.count()
        review = models.ReviewRequest.objects.create(
            requester=self.su,registration_authority=self.ra,
            state=self.ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )
        review.concepts.add(self.item1)
        with reversion.create_revision():
            self.item1.name = "change 2"
            reversion.set_comment("change 2")
            r = self.ra.register(
                item=self.item1,
                state=models.STATES.incomplete,
                user=self.registrar
            )
            self.item1.save()
        self.assertTrue(self.item1.statuses.count() == old_count + 1)
        
        from reversion.models import Version
        revisions = Version.objects.get_for_object(self.item1)

        response = self.client.get(
            reverse(
                "admin:%s_%s_compare"%(
                    self.itemType._meta.app_label,self.itemType._meta.model_name
                ),
                args=[self.item1.pk]
            ),
            {'version_id1' : revisions.first().pk,
            'version_id2' : revisions.last().pk
            }
        )
        self.assertResponseStatusCodeEqual(response,200)
        self.assertContains(response, "change 2")
        self.assertContains(response, 'statuses')
        
        self.item1 = self.itemType.objects.get(pk=self.item1.pk) #decache
        self.assertTrue(self.item1.name == "change 2")
        for s in self.item1.statuses.all():
            self.assertContains(
                response,
                '%s is %s'%(self.item1.name,s.get_state_display())
            )

    def test_editor_make_item_has_submitter(self):
        # Fixes #595
        self.login_editor()
        # make an item
        response = self.client.get(reverse("admin:%s_%s_add"%(self.itemType._meta.app_label,self.itemType._meta.model_name)))
        
        short_name = utils.id_generator()
        data = {
            'name':"admin_page_test_oc_has_submitter",
            'definition':"test", "workgroup":self.wg1.id,
            'short_name': short_name,
            'statuses-TOTAL_FORMS': 0, 'statuses-INITIAL_FORMS': 0 # no substatuses
        }
        data.update(self.form_defaults)

        response = self.client.post(
            reverse("admin:%s_%s_add"%(self.itemType._meta.app_label,self.itemType._meta.model_name)),
            data
        )
        new_item = self.itemType.objects.get(short_name=short_name)
        self.assertEqual(new_item.name,"admin_page_test_oc_has_submitter")
        self.assertEqual(new_item.submitter,self.editor)

        self.login_superuser()
        updated_item = dict((k,v) for (k,v) in model_to_dict(self.item1).items() if v is not None)
        updated_item['name'] = 'admin_page_test_oc_has_submitter_that_hasnt_changed'

        updated_item.update({
            'statuses-TOTAL_FORMS': 0, 'statuses-INITIAL_FORMS': 0, # no statuses
        })
        updated_item.update(self.form_defaults)

        response = self.client.post(
            reverse(
                "admin:%s_%s_change"%(self.itemType._meta.app_label,self.itemType._meta.model_name),
                args=[new_item.pk]
            ),
            updated_item
        )

        new_item = self.itemType.objects.get(pk=new_item.pk)  # decache
        self.assertEqual(new_item.name,"admin_page_test_oc_has_submitter_that_hasnt_changed")
        self.assertEqual(new_item.submitter,self.editor)


class ObjectClassAdminPage(AdminPageForConcept,TestCase):
    itemType=models.ObjectClass
class PropertyAdminPage(AdminPageForConcept,TestCase):
    itemType=models.Property
class ValueDomainAdminPage(AdminPageForConcept,TestCase):
    itemType=models.ValueDomain
    form_defaults={
        'permissiblevalue_set-TOTAL_FORMS':0,
        'permissiblevalue_set-INITIAL_FORMS':0,
        'permissiblevalue_set-MAX_NUM_FORMS':1,
        'supplementaryvalue_set-TOTAL_FORMS':0,
        'supplementaryvalue_set-INITIAL_FORMS':0,
        'supplementaryvalue_set-MAX_NUM_FORMS':1,
        }
class ConceptualDomainAdminPage(AdminPageForConcept,TestCase):
    itemType=models.ConceptualDomain
class DataElementConceptAdminPage(AdminPageForConcept,TestCase):
    itemType=models.DataElementConcept
class DataElementAdminPage(AdminPageForConcept,TestCase):
    itemType=models.DataElement
class DataTypeAdminPage(AdminPageForConcept,TestCase):
    itemType=models.DataType
class DataElementDerivationAdminPage(AdminPageForConcept,TestCase):
    itemType=models.DataElementDerivation
    def setUp(self):
        super(DataElementDerivationAdminPage, self).setUp(instant_create=False)
        from reversion import revisions as reversion
        with reversion.create_revision():
            self.ded_wg = models.Workgroup.objects.create(name="Derived WG")
            self.derived_de = models.DataElement.objects.create(name='derivedDE',definition="my definition",workgroup=self.ded_wg)

        self.ra.register(self.derived_de, models.STATES.standard, self.su)
        
        self.assertTrue(self.derived_de.is_public())
        self.create_items()


class OrganizationAdminPage(utils.LoggedInViewPages, TestCase):
    def test_registrar_cannot_promote_org_to_ra(self):
        self.login_registrar()

        org = models.Organization.objects.create(name="My org", definition="My new org")
        ra_count = models.RegistrationAuthority.objects.count()

        response = self.client.post(
            reverse('admin:%s_%s_changelist' % ('aristotle_mdr','organization')),
            {
                'action': "promote_to_ra",
                helpers.ACTION_CHECKBOX_NAME: [org.pk],
                "post":"yes"
            }
        )
        self.assertEqual(response.status_code, 302) # Redirects to admin login
        self.assertTrue(ra_count == models.RegistrationAuthority.objects.count())

    def test_admin_user_can_promote_org_to_ra(self):
        self.login_superuser()
        org = models.Organization.objects.create(name="My org", definition="My new org")
        ra_count = models.RegistrationAuthority.objects.count()
        org_count = models.Organization.objects.count()
        
        response = self.client.post(
            reverse('admin:%s_%s_changelist' % ('aristotle_mdr','organization')),
            {
                'action': "promote_to_ra",
                helpers.ACTION_CHECKBOX_NAME: [org.pk],
            }
        )
        msg = "Are you sure you want to promote the selected organizations to Registration Authorities"

        self.assertContains(response, msg)
        self.assertTrue(ra_count == models.RegistrationAuthority.objects.count())
        self.assertTrue(org_count == models.Organization.objects.count())

        response = self.client.post(
            reverse('admin:%s_%s_changelist' % ('aristotle_mdr','organization')),
            {
                'action': "promote_to_ra",
                helpers.ACTION_CHECKBOX_NAME: [org.pk],
                "post":"yes"
            }, follow=True
        )

        # We should have another registration authority
        self.assertEqual(ra_count + 1, models.RegistrationAuthority.objects.count())
        # BUT we should NOT have another organisation
        self.assertTrue(org_count == models.Organization.objects.count())

        msg = "Successfully promoted 1 organization."
        self.assertContains(response, msg)
