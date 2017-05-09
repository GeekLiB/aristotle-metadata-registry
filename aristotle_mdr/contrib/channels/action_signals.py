from channels import Group
from aristotle_mdr import models as MDR
from aristotle_mdr import messages
from aristotle_mdr.contrib.channels.utils import safe_object


def review_request_created(message, **kwargs):
    review_request = safe_object(message)
    registration_authorities = [review_request.registration_authority]  # Maybe this becomes a many to many later

    for ra in registration_authorities:
        for registrar in ra.registrars.all():
            messages.review_request_created(review_request, review_request.requester, registrar)


def review_request_updated(message, **kwargs):
    review_request = safe_object(message)
    messages.review_request_updated(review_request, review_request.requester, review_request.reviewer)
