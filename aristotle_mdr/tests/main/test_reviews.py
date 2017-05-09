from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings
import aristotle_mdr.models as models
import aristotle_mdr.perms as perms
import aristotle_mdr.tests.utils as utils
from aristotle_mdr.utils import url_slugify_concept

import datetime

from django.test.utils import setup_test_environment
setup_test_environment()


class ReviewRequestActionsPage(utils.LoggedInViewPages, TestCase):
    def setUp(self):
        super(ReviewRequestActionsPage, self).setUp()

        # There would be too many tests to test every item type against every other
        # But they all have identical logic, so one test should suffice
        self.item1 = models.ObjectClass.objects.create(name="Test Item 1 (visible to tested viewers)",definition="my definition",workgroup=self.wg1)
        self.item2 = models.ObjectClass.objects.create(name="Test Item 2 (NOT visible to tested viewers)",definition="my definition",workgroup=self.wg2)
        self.item3 = models.ObjectClass.objects.create(name="Test Item 3 (only visible to the editor)",definition="my definition",workgroup=None,submitter=self.editor)

    def test_viewer_cannot_request_review_for_private_item(self):
        self.login_viewer()

        response = self.client.get(reverse('aristotle:request_review',args=[self.item3.id]))
        self.assertEqual(response.status_code,403)

        response = self.client.get(reverse('aristotle:request_review',args=[self.item2.id]))
        self.assertEqual(response.status_code,403)

        response = self.client.get(reverse('aristotle:request_review',args=[self.item1.id]))
        self.assertEqual(response.status_code,200)

    def test_viewer_can_request_review(self):
        self.login_editor()

        response = self.client.get(reverse('aristotle:request_review',args=[self.item3.id]))
        self.assertEqual(response.status_code,200)

        response = self.client.get(reverse('aristotle:request_review',args=[self.item2.id]))
        self.assertEqual(response.status_code,403)

        response = self.client.get(reverse('aristotle:request_review',args=[self.item1.id]))
        self.assertEqual(response.status_code,200)
        form = response.context['form']

        self.assertEqual(self.item1.review_requests.count(),0)
        response = self.client.post(
            reverse('aristotle:request_review',args=[self.item1.id]),
            {
                'registration_authority': [str(self.ra.id)],
                'state': self.ra.public_state,
                'cascade_registration': 0,
                'message': "Please review this",
                'registration_date':datetime.date(2010,1,1)
            }
        )

        self.assertRedirects(response,url_slugify_concept(self.item1))
        self.assertEqual(self.item1.review_requests.count(),1)

    def test_registrar_has_valid_items_in_review(self):

        item1 = models.ObjectClass.objects.create(name="Test Item 1",definition="my definition",workgroup=self.wg1)
        item2 = models.ObjectClass.objects.create(name="Test Item 2",definition="my definition",workgroup=self.wg2)
        item3 = models.ObjectClass.objects.create(name="Test Item 3",definition="my definition",workgroup=self.wg1)
        item4 = models.ObjectClass.objects.create(name="Test Item 4",definition="my definition",workgroup=self.wg2)

        self.login_registrar()

        response = self.client.get(reverse('aristotle:userReadyForReview',))
        self.assertEqual(response.status_code,200)

        self.assertEqual(len(response.context['page']),0)

        review = models.ReviewRequest.objects.create(
            requester=self.su,
            registration_authority=self.ra,
            state=self.ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )

        review.concepts.add(item1)
        review.concepts.add(item4)

        response = self.client.get(reverse('aristotle:userReadyForReview',))
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['page']),1)

        review = models.ReviewRequest.objects.create(
            requester=self.su,
            registration_authority=self.ra,
            state=self.ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )

        review.concepts.add(item1)

        response = self.client.get(reverse('aristotle:userReadyForReview',))
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['page']),2)

        other_ra = models.RegistrationAuthority.objects.create(name="A different ra")
        review = models.ReviewRequest.objects.create(
            requester=self.su,
            registration_authority=other_ra,
            state=other_ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )

        review.concepts.add(item2)

        response = self.client.get(reverse('aristotle:userReadyForReview',))
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['page']),2)

        other_ra.giveRoleToUser('registrar',self.registrar)
        response = self.client.get(reverse('aristotle:userReadyForReview',))
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['page']),3)

    def test_superuser_can_see_review(self):
        self.login_superuser()
        other_ra = models.RegistrationAuthority.objects.create(name="A different ra")

        review = models.ReviewRequest.objects.create(
            requester=self.editor,
            registration_authority=other_ra,
            state=other_ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )

        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewDetails',args=[review.pk]))
        self.assertEqual(response.status_code,200)

        review = models.ReviewRequest.objects.create(
            requester=self.editor,
            registration_authority=self.ra,
            state=self.ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )

        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewDetails',args=[review.pk]))
        self.assertEqual(response.status_code,200)

        review.status = models.REVIEW_STATES.cancelled
        review.save()

        response = self.client.get(reverse('aristotle:userReviewDetails',args=[review.pk]))
        self.assertEqual(response.status_code,200)

    def test_registrar_can_see_review(self):
        self.login_registrar()
        other_ra = models.RegistrationAuthority.objects.create(name="A different ra")

        review = models.ReviewRequest.objects.create(
            requester=self.editor,
            registration_authority=other_ra,
            state=other_ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )

        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewDetails',args=[review.pk]))
        self.assertEqual(response.status_code,404)

        review = models.ReviewRequest.objects.create(
            requester=self.editor,
            registration_authority=self.ra,
            state=self.ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )

        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewDetails',args=[review.pk]))
        self.assertEqual(response.status_code,200)

        review.status = models.REVIEW_STATES.cancelled
        review.save()

        response = self.client.get(reverse('aristotle:userReviewDetails',args=[review.pk]))
        self.assertEqual(response.status_code,404)

    def test_anon_cannot_see_review(self):
        self.logout()

        review = models.ReviewRequest.objects.create(
            requester=self.editor,
            registration_authority=self.ra,
            state=self.ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )

        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewDetails',args=[review.pk]))
        self.assertEqual(response.status_code,302)
        # is redirected to login

    def test_editor_can_see_review(self):
        self.login_editor()

        review = models.ReviewRequest.objects.create(
            requester=self.editor,
            registration_authority=self.ra,
            state=self.ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )
        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewDetails',args=[review.pk]))
        self.assertEqual(response.status_code,200)

        review.status = models.REVIEW_STATES.cancelled
        review.save()

        response = self.client.get(reverse('aristotle:userReviewDetails',args=[review.pk]))
        self.assertEqual(response.status_code,200)

    def test_registrar_can_accept_review(self):
        self.login_registrar()
        other_ra = models.RegistrationAuthority.objects.create(name="A different ra")

        review = models.ReviewRequest.objects.create(
            requester=self.editor,
            registration_authority=other_ra,
            state=other_ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )
        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewAccept',args=[review.pk]))
        self.assertEqual(response.status_code,403)

        review = models.ReviewRequest.objects.create(
            requester=self.editor,
            registration_authority=self.ra,
            state=self.ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )
        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewAccept',args=[review.pk]))
        self.assertEqual(response.status_code,200)

        review.status = models.REVIEW_STATES.cancelled
        review.save()

        review = models.ReviewRequest.objects.get(pk=review.pk) #decache
        response = self.client.get(reverse('aristotle:userReviewAccept',args=[review.pk]))
        self.assertEqual(response.status_code,403)
        
        response = self.client.post(reverse('aristotle:userReviewAccept',args=[review.pk]),
            {
                'response':"I can't accept this, its cancelled"
            })

        review = models.ReviewRequest.objects.get(pk=review.pk) #decache
        self.assertEqual(response.status_code,403)
        self.assertEqual(review.status, models.REVIEW_STATES.cancelled)
        self.assertTrue(bool(review.response) == False)

        review.status = models.REVIEW_STATES.submitted
        review.save()

        self.assertTrue(self.item1.current_statuses().count() == 0)

        self.item1 = models.ObjectClass.objects.get(pk=self.item1.pk) # decache
        self.assertFalse(self.item1.is_public())

        response = self.client.post(reverse('aristotle:userReviewAccept',args=[review.pk]),
            {
                'response':"I can accept this!",
            })
        self.assertRedirects(response,reverse('aristotle:userReadyForReview',))

        review = models.ReviewRequest.objects.get(pk=review.pk) #decache
        self.assertEqual(review.response, "I can accept this!")
        self.assertEqual(review.status,models.REVIEW_STATES.accepted)
        self.assertEqual(review.reviewer, self.registrar)

        self.item1 = models.ObjectClass.objects.get(pk=self.item1.pk) # decache
        self.assertTrue(self.item1.is_public())
        self.assertTrue(self.item1.current_statuses().count() == 1)
        state = self.item1.current_statuses().first()

        self.assertTrue(state.registrationAuthority == review.registration_authority)
        self.assertTrue(state.state == review.state)
        self.assertTrue(state.registrationDate == review.registration_date)


    def test_registrar_can_reject_review(self):
        self.login_registrar()
        other_ra = models.RegistrationAuthority.objects.create(name="A different ra")

        review = models.ReviewRequest.objects.create(
            requester=self.editor,
            registration_authority=other_ra,
            state=other_ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )

        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewReject',args=[review.pk]))
        self.assertEqual(response.status_code,403)

        review = models.ReviewRequest.objects.create(
            requester=self.editor,
            registration_authority=self.ra,
            state=self.ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )

        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewReject',args=[review.pk]))
        self.assertEqual(response.status_code,200)

        review.status = models.REVIEW_STATES.cancelled
        review.save()

        review = models.ReviewRequest.objects.get(pk=review.pk) #decache
        response = self.client.get(reverse('aristotle:userReviewReject',args=[review.pk]))
        self.assertEqual(response.status_code,403)
        
        response = self.client.post(reverse('aristotle:userReviewReject',args=[review.pk]),
            {
                'response':"I can't reject this, its cancelled"
            })

        review = models.ReviewRequest.objects.get(pk=review.pk) #decache
        self.assertEqual(response.status_code,403)
        self.assertEqual(review.status, models.REVIEW_STATES.cancelled)
        self.assertTrue(bool(review.response) == False)

        review.status = models.REVIEW_STATES.submitted
        review.save()

        response = self.client.post(reverse('aristotle:userReviewReject',args=[review.pk]),
            {
                'response':"I can reject this!",
            })
        #self.assertEqual(response.status_code,200)
        self.assertRedirects(response,reverse('aristotle:userReadyForReview',))

        review = models.ReviewRequest.objects.get(pk=review.pk) #decache
        self.assertEqual(review.response, "I can reject this!")
        self.assertEqual(review.status,models.REVIEW_STATES.rejected)
        self.assertEqual(review.reviewer, self.registrar)

        self.item1 = models.ObjectClass.objects.get(pk=self.item1.pk) # decache
        self.assertFalse(self.item1.is_public())

    def test_user_can_cancel_review(self):
        self.login_editor()

        review = models.ReviewRequest.objects.create(
            requester=self.viewer,
            registration_authority=self.ra,
            state=self.ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )

        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewCancel',args=[review.pk]))
        self.assertEqual(response.status_code,403)

        review = models.ReviewRequest.objects.create(
            requester=self.editor,
            registration_authority=self.ra,
            state=self.ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )

        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewCancel',args=[review.pk]))
        self.assertEqual(response.status_code,200)

        review.status = models.REVIEW_STATES.cancelled
        review.save()

        response = self.client.get(reverse('aristotle:userReviewCancel',args=[review.pk]))
        self.assertRedirects(response,reverse('aristotle:userReviewDetails',args=[review.pk]))

        review = models.ReviewRequest.objects.create(
            requester=self.editor,
            registration_authority=self.ra,
            state=self.ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )

        review.concepts.add(self.item1)

        self.assertFalse(review.status == models.REVIEW_STATES.cancelled)        
        response = self.client.post(reverse('aristotle:userReviewCancel',args=[review.pk]),{})
        self.assertRedirects(response,reverse('aristotle:userMyReviewRequests',))

        review = models.ReviewRequest.objects.get(pk=review.pk) #decache
        self.assertTrue(review.status == models.REVIEW_STATES.cancelled)

    def test_registrar_cant_load_rejected_or_accepted_review(self):
        self.login_registrar()
        other_ra = models.RegistrationAuthority.objects.create(name="A different ra")

        review = models.ReviewRequest.objects.create(
            requester=self.editor,
            registration_authority=self.ra,
            status=models.REVIEW_STATES.accepted,
            state=models.STATES.standard,
            registration_date=datetime.date(2010,1,1)
        )

        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewReject',args=[review.pk]))
        self.assertRedirects(response,reverse('aristotle_mdr:userReviewDetails', args=[review.pk]))

        response = self.client.get(reverse('aristotle:userReviewAccept',args=[review.pk]))
        self.assertRedirects(response,reverse('aristotle_mdr:userReviewDetails', args=[review.pk]))

        review = models.ReviewRequest.objects.create(
            requester=self.editor,
            registration_authority=self.ra,
            status=models.REVIEW_STATES.rejected,
            state=models.STATES.standard,
            registration_date=datetime.date(2010,1,1)
        )

        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewReject',args=[review.pk]))
        self.assertRedirects(response,reverse('aristotle_mdr:userReviewDetails', args=[review.pk]))

        response = self.client.get(reverse('aristotle:userReviewAccept',args=[review.pk]))
        self.assertRedirects(response,reverse('aristotle_mdr:userReviewDetails', args=[review.pk]))

        review = models.ReviewRequest.objects.create(
            requester=self.editor,
            registration_authority=self.ra,
            status=models.REVIEW_STATES.cancelled,
            state=models.STATES.standard,
            registration_date=datetime.date(2010,1,1)
        )

        review.concepts.add(self.item1)

        response = self.client.get(reverse('aristotle:userReviewReject',args=[review.pk]))
        self.assertEqual(response.status_code,403)
        response = self.client.get(reverse('aristotle:userReviewAccept',args=[review.pk]))
        self.assertEqual(response.status_code,403)

    def test_who_can_see_review(self):
        from aristotle_mdr.perms import user_can_view_review

        review = models.ReviewRequest.objects.create(
            requester=self.editor,
            registration_authority=self.ra,
            state=self.ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )

        review.concepts.add(self.item1)

        self.assertTrue(user_can_view_review(self.editor,review))
        self.assertTrue(user_can_view_review(self.registrar,review))
        self.assertTrue(user_can_view_review(self.su,review))
        self.assertFalse(user_can_view_review(self.viewer,review))
        
        review.status = models.REVIEW_STATES.cancelled
        review.save()

        review = models.ReviewRequest.objects.get(pk=review.pk) #decache

        self.assertTrue(user_can_view_review(self.editor,review))
        self.assertFalse(user_can_view_review(self.registrar,review))
        self.assertTrue(user_can_view_review(self.su,review))
        self.assertFalse(user_can_view_review(self.viewer,review))

    def test_notifications(self):
        viewer_num_notifications = self.viewer.notifications.count()
        registrar_num_notifications = self.registrar.notifications.count()
        editor_num_notifications = self.editor.notifications.count()

        review = models.ReviewRequest.objects.create(
            requester=self.viewer,
            registration_authority=self.ra,
            state=self.ra.public_state,
            registration_date=datetime.date(2010,1,1)
        )

        # Review requested, does a registrar get the notification?
        self.assertTrue(self.viewer.notifications.count() == viewer_num_notifications)
        self.assertTrue(self.registrar.notifications.count() == registrar_num_notifications + 1)
        self.assertTrue(self.editor.notifications.count() == editor_num_notifications)

        self.assertTrue(self.registrar.notifications.first().target == review)

        review.status = models.REVIEW_STATES.accepted
        review.save()

        # Review updated, does the requester get the notification?
        self.assertTrue(self.viewer.notifications.count() == viewer_num_notifications + 1)
        self.assertTrue(self.registrar.notifications.count() == registrar_num_notifications + 1)
        self.assertTrue(self.editor.notifications.count() == editor_num_notifications)

        self.assertTrue(self.viewer.notifications.first().target == review)
