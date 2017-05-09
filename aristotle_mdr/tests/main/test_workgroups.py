from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
import aristotle_mdr.models as models
import aristotle_mdr.perms as perms
import aristotle_mdr.tests.utils as utils

from django.test.utils import setup_test_environment
setup_test_environment()

# This is for testing permissions around workgroup mangement.

class WorkgroupMembership(TestCase):
    def test_userInWorkgroup(self):
        wg = models.Workgroup.objects.create(name="Test WG 1")
        user = User.objects.create_user('editor1','','editor1')
        wg.viewers.add(user)
        self.assertTrue(perms.user_in_workgroup(user,wg))
    def test_RemoveUserFromWorkgroup(self):
        # Does removing a user from a workgroup remove their permissions? It should!
        wg = models.Workgroup.objects.create(name="Test WG 1")
        user = User.objects.create_user('editor1','','editor1')
        wg.managers.add(user)
        # Caching issue, refresh from DB with correct permissions
        user = User.objects.get(pk=user.pk)
        self.assertTrue(perms.user_in_workgroup(user,wg))
        self.assertTrue(perms.user_is_workgroup_manager(user,wg))
        wg.removeUser(user)
        # Caching issue, refresh from DB with correct permissions
        user = User.objects.get(pk=user.pk)
        self.assertFalse(perms.user_is_workgroup_manager(user,wg))
    def test_managersCanEditWorkgroups(self):
        wg = models.Workgroup.objects.create(name="Test WG 1")
        user1 = User.objects.create_user('manager','','manager')
        user2 = User.objects.create_user('viewer','','viewer')
        wg.managers.add(user1)
        wg.viewers.add(user2)
        wg.save()
        wg = models.Workgroup.objects.get(pk=wg.id)

        self.assertTrue(perms.user_in_workgroup(user1,wg))
        self.assertTrue(perms.user_in_workgroup(user2,wg))
        self.assertTrue(perms.user_can_view(user2,wg))
        self.assertTrue(perms.user_can_view(user1,wg))

        self.assertTrue(perms.user_can_edit(user1,wg))
        self.assertFalse(perms.user_can_edit(user2,wg))
        wg.removeUser(user1)
        wg.removeUser(user2)
        # Caching issue, refresh from DB with correct permissions
        user1 = User.objects.get(pk=user1.pk)
        user2 = User.objects.get(pk=user2.pk)
        self.assertFalse(perms.user_can_edit(user1,wg))
        self.assertFalse(perms.user_can_edit(user2,wg))

    def test_editable_workgroups_are_unique(self):
        # Tests against bug #333
        # https://github.com/aristotle-mdr/aristotle-metadata-registry/issues/333
        wg1 = models.Workgroup.objects.create(name="Test WG 1")
        wg2 = models.Workgroup.objects.create(name="Test WG 2")
        wg3 = models.Workgroup.objects.create(name="Test WG 3")
        editor = User.objects.create_user('editor','','editor')
        wg1.stewards.add(editor)
        wg1.submitters.add(editor)
        wg1.viewers.add(editor)
        wg2.stewards.add(editor)
        wg3.viewers.add(editor)
        wg1.save()
        wg2.save()
        wg3.save()

        editor = User.objects.get(pk=editor.pk)
        
        editable = editor.profile.editable_workgroups
        self.assertTrue(editable.count() == 2)
        self.assertTrue(wg1 in editable.all())
        self.assertTrue(wg2 in editable.all())
        self.assertTrue(wg3 not in editable.all())

class WorkgroupAnonTests(utils.LoggedInViewPages,TestCase):
    def setUp(self):
        super(WorkgroupAnonTests, self).setUp()
        self.newuser = User.objects.create_user('nathan','','noobie')
        self.newuser.save()

    def test_anon_cannot_add(self):
        self.logout()
        response = self.client.get(reverse('aristotle:addWorkgroupMembers',args=[self.wg1.id]))
        self.assertRedirects(response,
            reverse("friendly_login",)+"?next="+
            reverse('aristotle:addWorkgroupMembers',args=[self.wg1.id])
            )

        response = self.client.get(reverse('aristotle:removeWorkgroupRole',args=[self.wg1.id,'Viewer',self.newuser.pk]))
        self.assertRedirects(response,
            reverse("friendly_login",)+"?next="+
            reverse('aristotle:removeWorkgroupRole',args=[self.wg1.id,'Viewer',self.newuser.pk])
            )

        response = self.client.post(
            reverse('aristotle:addWorkgroupMembers',args=[self.wg1.id]),
            {
                'roles':['Viewer'],
                'users':[self.newuser.pk]
            }
        )
        self.assertRedirects(
            response,
            reverse("friendly_login",)+"?next="+
            reverse('aristotle:addWorkgroupMembers', args=[self.wg1.id])
        )
        self.assertListEqual(list(self.newuser.profile.workgroups.all()),[])

class WorkgroupMemberTests(utils.LoggedInViewPages,TestCase):
    def setUp(self):
        super(WorkgroupMemberTests, self).setUp()
        self.newuser = User.objects.create_user('nathan','','noobie')
        self.newuser.save()

    def test_userCanLeaveWorkgroup(self):
        self.login_viewer()
        response = self.client.get(self.wg1.get_absolute_url())
        self.assertEqual(response.status_code,200)

        self.assertTrue(perms.user_in_workgroup(self.viewer,self.wg1))

        response = self.client.get(reverse('aristotle:workgroup_leave',args=[self.wg1.id]))
        self.assertEqual(response.status_code,200)

        response = self.client.post(reverse('aristotle:workgroup_leave',args=[self.wg1.id]))
        self.assertEqual(response.status_code,302)

        response = self.client.get(self.wg1.get_absolute_url())
        self.assertEqual(response.status_code,403)

    def test_viewer_cannot_add_or_remove_users(self):
        self.login_viewer()
        response = self.client.get(reverse('aristotle:addWorkgroupMembers',args=[self.wg1.id]))
        self.assertEqual(response.status_code,403)
        response = self.client.get(reverse('aristotle:removeWorkgroupRole',args=[self.wg1.id,'Viewer',self.newuser.pk]))
        self.assertEqual(response.status_code,403)

    def test_manager_can_add_or_remove_users(self):
        self.login_manager()
        self.assertTrue(self.newuser in list(User.objects.all()))

        response = self.client.get(reverse('aristotle:addWorkgroupMembers',args=[self.wg2.id]))
        self.assertEqual(response.status_code,403)
        response = self.client.get(reverse('aristotle:addWorkgroupMembers',args=[self.wg1.id]))
        self.assertEqual(response.status_code,200)
        self.assertTrue(self.newuser.id in [u[0] for u in response.context['form'].fields['users'].choices])

        self.assertListEqual(list(self.newuser.profile.workgroups.all()),[])
        response = self.client.post(
            reverse('aristotle:addWorkgroupMembers', args=[self.wg2.id]),
            {
                'roles':['viewer'],
                'users':[self.newuser.pk]
            }
        )
        self.assertEqual(response.status_code,403)
        self.assertListEqual(list(self.newuser.profile.workgroups.all()),[])

        response = self.client.post(
            reverse('aristotle:addWorkgroupMembers', args=[self.wg1.id]),
            {
                'roles': ['viewer'],
                'users': [self.newuser.pk]
            }
        )
        self.assertEqual(response.status_code,302)
        self.assertTrue(self.newuser in self.wg1.members.all())
        self.assertListEqual(list(self.newuser.profile.workgroups.all()),[self.wg1])

        response = self.client.get(reverse('aristotle:removeWorkgroupRole',args=[self.wg1.id,'viewer',self.newuser.pk]))
        self.assertEqual(response.status_code,302)
        self.assertFalse(self.newuser in self.wg1.viewers.all())
        response = self.client.get(reverse('aristotle:removeWorkgroupRole',args=[self.wg1.id,'viewer',self.newuser.pk]))
        self.assertEqual(response.status_code,302)
        self.assertFalse(self.newuser in self.wg1.viewers.all())

    def test_workgroup_members_can_view_pages(self):
        self.logout()
        # Anonymous user can't see workgroup pages
        n = reverse('friendly_login')+"?next="
        response = self.client.get(reverse('aristotle:workgroup',args=[self.wg1.id]))
        self.assertRedirects(response,n+reverse('aristotle:workgroup',args=[self.wg1.id]),302,200)
        response = self.client.get(reverse('aristotle:workgroupMembers',args=[self.wg1.id]))
        self.assertRedirects(response,n+reverse('aristotle:workgroupMembers',args=[self.wg1.id]),302,200)
        response = self.client.get(reverse('aristotle:workgroupItems',args=[self.wg1.id]))
        self.assertRedirects(response,n+reverse('aristotle:workgroupItems',args=[self.wg1.id]),302,200)

        # Logged in non-member can't see workgroup pages
        response = self.client.post(reverse('friendly_login'), {'username': 'nathan', 'password': 'noobie'})
        response = self.client.get(reverse('aristotle:workgroup',args=[self.wg1.id]))
        self.assertEqual(response.status_code,302) # can't use assertRedirect as we redirect to a forbidden page?

        response = self.client.get(self.wg1.get_absolute_url())
        self.assertEqual(response.status_code,403)

        response = self.client.get(reverse('aristotle:workgroupMembers',args=[self.wg1.id]))
        self.assertEqual(response.status_code,403)
        response = self.client.get(reverse('aristotle:workgroupItems',args=[self.wg1.id]))
        self.assertEqual(response.status_code,403)

        self.login_viewer()
        response = self.client.get(reverse('aristotle:workgroup',args=[self.wg1.id]))
        self.assertRedirects(response,self.wg1.get_absolute_url())
        self.assertEqual(response.status_code,302)
        response = self.client.get(self.wg1.get_absolute_url())
        self.assertEqual(response.status_code,200)
        response = self.client.get(reverse('aristotle:workgroupMembers',args=[self.wg1.id]))
        self.assertEqual(response.status_code,200)
        response = self.client.get(reverse('aristotle:workgroupItems',args=[self.wg1.id]))
        self.assertEqual(response.status_code,200)
        response = self.client.get(reverse('aristotle:workgroupItems',args=[self.wg1.id])+"?page=100") # deliberately overshoot
        self.assertEqual(response.status_code,200)

        self.login_manager()

        response = self.client.get(reverse('aristotle:workgroup',args=[self.wg1.id]))
        self.assertEqual(response.status_code,302)
        response = self.client.get(self.wg1.get_absolute_url())
        self.assertEqual(response.status_code,200)
        response = self.client.get(reverse('aristotle:workgroupMembers',args=[self.wg1.id]))
        self.assertEqual(response.status_code,200)
        response = self.client.get(reverse('aristotle:workgroupItems',args=[self.wg1.id]))

    def test_manager_can_archive(self):
        self.login_viewer()
        # Viewers cannot archive
        response = self.client.get(reverse('aristotle:archive_workgroup',args=[self.wg1.id]))
        self.assertEqual(response.status_code,403)
        response = self.client.get(reverse('aristotle:archive_workgroup',args=[self.wg2.id]))
        self.assertEqual(response.status_code,403)

        # Viewers shouldn't even have the button on the workgroup page
        response = self.client.get(self.wg1.get_absolute_url())
        self.assertNotContains(response, "archive_modal")

        self.login_manager()

        # Managers must even have the archive button on the workgroup page
        response = self.client.get(self.wg1.get_absolute_url())
        self.assertNotContains(response, "archive_modal")

        response = self.client.get(reverse('aristotle:archive_workgroup',args=[self.wg2.id]))
        self.assertEqual(response.status_code,403)
        response = self.client.get(reverse('aristotle:archive_workgroup',args=[self.wg1.id]))
        self.assertEqual(response.status_code,200)
        self.assertFalse(self.wg1.archived)
        self.assertTrue(self.wg1 in self.viewer.profile.myWorkgroups)

        response = self.client.post(reverse('aristotle:archive_workgroup',args=[self.wg1.id]),{})
        self.assertRedirects(response,self.wg1.get_absolute_url())

        self.wg1 = models.Workgroup.objects.get(pk=self.wg1.pk) # refetch
        self.assertTrue(self.wg1.archived)
        self.assertTrue(self.wg1 not in self.viewer.profile.myWorkgroups)

        response = self.client.post(reverse('aristotle:archive_workgroup',args=[self.wg1.id]),{})
        self.assertRedirects(response,self.wg1.get_absolute_url())
        self.wg1 = models.Workgroup.objects.get(pk=self.wg1.pk) # refetch
        self.assertFalse(self.wg1.archived)
        self.assertTrue(self.wg1 in self.viewer.profile.myWorkgroups)
