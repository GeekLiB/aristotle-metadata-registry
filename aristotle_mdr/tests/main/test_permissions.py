from __future__ import print_function

from django.contrib.auth.models import User
from django.test import TestCase
from django.test.utils import setup_test_environment

import datetime

import aristotle_mdr.models as models
import aristotle_mdr.perms as perms
from aristotle_mdr.tests import utils

setup_test_environment()

class SuperuserPermissions(TestCase):
    # All of the below are called with None as a Superuser, by definition *must* be able to edit, view and managed everything. Since a is_superuser chcek is cheap is should be called first, so calling with None checks that there is no other database calls going on.
    def setUp(self):
        self.su=User.objects.create_superuser('super','','user')

    def test_user_can_alter_comment(self):
        self.assertTrue(perms.user_can_alter_comment(self.su,None))
    def test_user_can_alter_post(self):
        self.assertTrue(perms.user_can_alter_post(self.su,None))
    def test_can_view(self):
        self.assertTrue(perms.user_can_view(self.su,None))
    def test_is_editor(self):
        self.assertTrue(perms.user_is_editor(self.su))
    def test_is_registrar(self):
        self.assertTrue(perms.user_is_registrar(self.su))
        ra = models.RegistrationAuthority.objects.create(name="Test RA")
        self.assertTrue(perms.user_is_registrar(self.su,ra))
    def test_is_workgroup_manager(self):
        self.assertTrue(perms.user_is_workgroup_manager(self.su,None))
        wg = models.Workgroup.objects.create(name="Test WG")
        self.assertTrue(perms.user_is_workgroup_manager(self.su,wg))
    def test_can_change_status(self):
        self.assertTrue(perms.user_can_change_status(self.su,None))
    def test_can_edit(self):
        self.assertTrue(perms.user_can_edit(self.su,None))
    def test_in_workgroup(self):
        self.assertTrue(perms.user_in_workgroup(self.su,None))
    def test_can_edit_registration_authority(self):
        ra = models.RegistrationAuthority.objects.create(name="Test RA")
        self.assertTrue(ra.can_edit(self.su))

class UnitOfMeasureVisibility(utils.ManagedObjectVisibility,TestCase):
    def setUp(self):
        super(UnitOfMeasureVisibility, self).setUp()
        self.item = models.UnitOfMeasure.objects.create(name="Test UOM",workgroup=self.wg)

class ObjectClassVisibility(utils.ManagedObjectVisibility,TestCase):
    def setUp(self):
        super(ObjectClassVisibility, self).setUp()
        self.item = models.ObjectClass.objects.create(name="Test OC",workgroup=self.wg)
class PropertyVisibility(utils.ManagedObjectVisibility,TestCase):
    def setUp(self):
        super(PropertyVisibility, self).setUp()
        self.item = models.Property.objects.create(name="Test P",workgroup=self.wg)
class ValueDomainVisibility(utils.ManagedObjectVisibility,TestCase):
    def setUp(self):
        super(ValueDomainVisibility, self).setUp()
        self.item = models.ValueDomain.objects.create(
            name="Test VD",
            workgroup=self.wg,
            format="X" ,
            maximum_length=3,
            data_type=models.DataType.objects.create(name="Test DT", workgroup=self.wg)
        )
class DataElementConceptVisibility(utils.ManagedObjectVisibility,TestCase):
    def setUp(self):
        super(DataElementConceptVisibility, self).setUp()
        self.item = models.DataElementConcept.objects.create(
            name="Test DEC",
            workgroup=self.wg,
        )
class DataElementVisibility(utils.ManagedObjectVisibility,TestCase):
    def setUp(self):
        super(DataElementVisibility, self).setUp()
        self.item = models.DataElement.objects.create(
            name="Test DE",
            workgroup=self.wg,
        )
class DataTypeVisibility(utils.ManagedObjectVisibility,TestCase):
    def setUp(self):
        super(DataTypeVisibility, self).setUp()
        self.item = models.DataType.objects.create(
            name="Test DT",
            workgroup=self.wg,
        )

class WorkgroupPermissions(TestCase):
    def test_workgroup_add_members(self):
        wg = models.Workgroup.objects.create(name="Test WG")
        user = User.objects.create_user('user','','user')

        wg.giveRoleToUser('manager',user)
        self.assertTrue(user in wg.managers.all())
        wg.removeRoleFromUser('manager',user)
        self.assertFalse(user in wg.managers.all())

        wg.giveRoleToUser('viewer',user)
        self.assertTrue(user in wg.viewers.all())
        wg.removeRoleFromUser('viewer',user)
        self.assertFalse(user in wg.viewers.all())

        wg.giveRoleToUser('submitter',user)
        self.assertTrue(user in wg.submitters.all())
        wg.removeRoleFromUser('submitter',user)
        self.assertFalse(user in wg.submitters.all())

        wg.giveRoleToUser('steward',user)
        self.assertTrue(user in wg.stewards.all())
        wg.removeRoleFromUser('steward',user)
        self.assertFalse(user in wg.stewards.all())

class RegistryGroupPermissions(TestCase):
    def test_registration_add_members(self):
        ra = models.RegistrationAuthority.objects.create(name="Test RA")
        user = User.objects.create_user('user','','user')

        ra.giveRoleToUser('registrar',user)
        self.assertTrue(user in ra.registrars.all())
        ra.removeRoleFromUser('registrar',user)
        self.assertFalse(user in ra.registrars.all())

        ra.giveRoleToUser('manager',user)
        self.assertTrue(user in ra.managers.all())
        ra.removeRoleFromUser('manager',user)
        self.assertFalse(user in ra.managers.all())

    def test_RegistrationAuthority_name_change(self):
        ra = models.RegistrationAuthority.objects.create(name="Test RA")
        user = User.objects.create_user('registrar','','registrar')

        # User isn't in RA... yet
        self.assertFalse(perms.user_is_registrar(user,ra))

        # Add user to RA, assert user is in RA
        ra.giveRoleToUser('registrar',user)
        # Caching issue, refresh from DB with correct permissions
        user = User.objects.get(pk=user.pk)
        self.assertTrue(perms.user_is_registrar(user,ra))

        # Change name of RA, assert user is still in RA
        ra.name = "Test RA2"
        ra.save()
        user = User.objects.get(pk=user.pk)
        self.assertTrue(perms.user_is_registrar(user,ra))

        # Add new RA with old RA's name, assert user is not in the new RA
        newRA = models.RegistrationAuthority.objects.create(name="Test RA")
        user = User.objects.get(pk=user.pk)
        self.assertFalse(perms.user_is_registrar(user,newRA))

        # Remove user to RA, assert user is no longer in RA
        ra.removeRoleFromUser('registrar',user)
        # Caching issue, refresh from DB with correct permissions
        user = User.objects.get(pk=user.pk)
        self.assertFalse(perms.user_is_registrar(user,ra))

class UserEditTesting(TestCase):
    def test_canViewProfile(self):
        u1 = User.objects.create_user('user1','','user1')
        u2 = User.objects.create_user('user2','','user2')
        self.assertFalse(perms.user_can_view(u1,u2))
        self.assertFalse(perms.user_can_view(u2,u1))
        self.assertTrue(perms.user_can_view(u1,u1))
        self.assertTrue(perms.user_can_view(u2,u2))
    def test_canEditProfile(self):
        u1 = User.objects.create_user('user1','','user1')
        u2 = User.objects.create_user('user2','','user2')
        self.assertFalse(perms.user_can_edit(u1,u2))
        self.assertFalse(perms.user_can_edit(u2,u1))
        self.assertTrue(perms.user_can_edit(u1,u1))
        self.assertTrue(perms.user_can_edit(u2,u2))


class CustomConceptQuerySetTest(TestCase):
    def test_is_public_as_changes_happen(self):
        # Uses ValueDomain so the querysets don't return things created in `setUpClass`.
        ra = models.RegistrationAuthority.objects.create(name="Test RA",public_state=models.STATES.standard)
        wg = models.Workgroup.objects.create(name="Setup WG")
        wg.save()
        oc1 = models.ValueDomain.objects.create(name="Test OC1",workgroup=wg)
        oc2 = models.ValueDomain.objects.create(name="Test OC2",workgroup=wg)
        user = User.objects.create_superuser('super','','user')

        # Assert no public items
        self.assertEqual(len(models.ValueDomain.objects.all().public()),0)

        # Register OC1 only
        ra.register(oc1,models.STATES.standard,user,registrationDate=datetime.date(2010,10,1))

        # Assert only OC1 is public
        self.assertEqual(len(models.ValueDomain.objects.all().public()),1)
        self.assertTrue(oc1 in models.ValueDomain.objects.all().public())
        self.assertTrue(oc2 not in models.ValueDomain.objects.all().public())

        from time import sleep
        sleep(2)
        # Sleep for 2 seconds, as MMSQL is seeing both registrations as having the 'same' creation time

        # Deregister OC1
        state=models.STATES.incomplete
        regDate=datetime.date(2010,10,1)
        registration_attempt = ra.register(oc1,state,user,registrationDate=regDate)

        oc1 = models.ValueDomain.objects.get(pk=oc1.pk)

        self.assertTrue(registration_attempt['failed'] == [])
        self.assertTrue(len(oc1.current_statuses()) == 1)
        self.assertTrue(oc1.current_statuses().first().registrationDate == regDate)
        self.assertFalse(oc1._is_public)

        # Assert no public items
        self.assertTrue(oc1 not in models.ValueDomain.objects.all().public())
        self.assertEqual(len(models.ValueDomain.objects.all().public()),0)

class RegistryCascadeTest(TestCase):
    def test_superuser_DataElementConceptCascade(self):
        user = User.objects.create_superuser('super','','user')
        self.ra = models.RegistrationAuthority.objects.create(name="Test RA - cascading")
        self.wg = models.Workgroup.objects.create(name="Setup WG")
        self.wg.save()
        self.oc = models.ObjectClass.objects.create(name="Test OC",workgroup=self.wg)
        self.pr = models.Property.objects.create(name="Test P",workgroup=self.wg)
        self.dec = models.DataElementConcept.objects.create(
            name="Test DEC",
            objectClass=self.oc,
            property=self.pr,
            workgroup=self.wg,
        )

        self.assertEqual(self.oc.statuses.count(),0)
        self.assertEqual(self.pr.statuses.count(),0)
        self.assertEqual(self.dec.statuses.count(),0)

        state=models.STATES.candidate
        self.ra.register(self.dec,state,user,registrationDate=datetime.date(2001,10,1),changeDetails='test DEC register')
        self.assertEqual(self.oc.statuses.count(),0)
        self.assertEqual(self.pr.statuses.count(),0)
        self.assertEqual(self.dec.statuses.count(),1)

        state=models.STATES.standard
        self.ra.cascaded_register(self.dec,state,user,registrationDate=datetime.date(2010,10,1),changeDetails='test DEC cascade register')
        self.assertEqual(len(self.dec.current_statuses()),1)
        self.assertEqual(len(self.oc.current_statuses()),1)
        self.assertEqual(len(self.pr.current_statuses()),1)

        self.assertEqual(self.oc.current_statuses()[0].state,state)
        self.assertEqual(self.pr.current_statuses()[0].state,state)
        self.assertEqual(self.dec.current_statuses()[0].state,state)

    def test_superuser_DataElementCascade(self):
        user = User.objects.create_superuser('super','','user')
        self.ra = models.RegistrationAuthority.objects.create(name="Test RA")
        self.wg = models.Workgroup.objects.create(name="Setup WG")
        self.wg.save()
        self.oc = models.ObjectClass.objects.create(name="Test OC",workgroup=self.wg)
        self.pr = models.Property.objects.create(name="Test P",workgroup=self.wg)
        self.vd = models.ValueDomain.objects.create(
            name="Test VD",
            workgroup=self.wg,
            format = "X" ,
            maximum_length = 3,
            data_type = models.DataType.objects.create(name="Test DT",workgroup=self.wg)
        )
        self.dec = models.DataElementConcept.objects.create(
            name="Test DEC",
            objectClass=self.oc,
            property=self.pr,
            workgroup=self.wg,
        )
        self.de = models.DataElement.objects.create(
            name="Test DE",
            dataElementConcept=self.dec,
            valueDomain=self.vd,
            workgroup=self.wg,
        )

        self.assertEqual(self.oc.statuses.count(),0)
        self.assertEqual(self.pr.statuses.count(),0)
        self.assertEqual(self.vd.statuses.count(),0)
        self.assertEqual(self.dec.statuses.count(),0)
        self.assertEqual(self.de.statuses.count(),0)

        state=models.STATES.candidate
        self.ra.register(self.de,state,user,registrationDate=datetime.date(2001,10,1),)
        self.assertEqual(len(self.oc.current_statuses()),0)
        self.assertEqual(len(self.pr.current_statuses()),0)
        self.assertEqual(len(self.vd.current_statuses()),0)
        self.assertEqual(len(self.dec.current_statuses()),0)
        self.assertEqual(len(self.de.current_statuses()),1)

        state=models.STATES.standard
        self.ra.cascaded_register(self.de,state,user,registrationDate=datetime.date(2010,10,1),)
        self.assertEqual(len(self.de.current_statuses()),1)
        self.assertEqual(len(self.dec.current_statuses()),1)
        self.assertEqual(len(self.vd.current_statuses()),1)
        self.assertEqual(len(self.oc.current_statuses()),1)
        self.assertEqual(len(self.pr.current_statuses()),1)

        self.assertEqual(self.oc.current_statuses()[0].state,state)
        self.assertEqual(self.pr.current_statuses()[0].state,state)
        self.assertEqual(self.vd.current_statuses()[0].state,state)
        self.assertEqual(self.dec.current_statuses()[0].state,state)
        self.assertEqual(self.de.current_statuses()[0].state,state)
