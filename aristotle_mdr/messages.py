from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from notifications.signals import notify


def favourite_updated(recipient, obj):
    notify.send(obj, recipient=recipient, verb="A favourited item has been changed:", target=obj)


def favourite_superseded(recipient, obj):
    notify.send(obj, recipient=recipient, verb="A favourited item has been superseded:", target=obj)


def registrar_item_superseded(recipient, obj):
    notify.send(obj, recipient=recipient, verb="A item registered by your registration authority has been superseded:", target=obj)


def registrar_item_registered(recipient, obj):
    notify.send(obj, recipient=recipient, verb="A item has been registered by your registration authority:", target=obj)


def registrar_item_changed_status(recipient, obj):
    notify.send(obj, recipient=recipient, verb="A item registered by your registration authority has changed status:", target=obj)


def workgroup_item_updated(recipient, obj):
    notify.send(obj, recipient=recipient, verb="was modified in the workgroup", target=obj.workgroup)


def workgroup_item_new(recipient, obj):
    notify.send(obj, recipient=recipient, verb="was modified in the workgroup", target=obj.workgroup)


def new_comment_created(comment):
    post = comment.post
    author_name = comment.author.get_full_name() or comment.author
    notify.send(comment.author, recipient=post.author, verb="commented on your post", target=post)


def new_post_created(post, recipient):
    op_name = post.author.get_full_name() or post.author
    notify.send(post.author, recipient=recipient, verb="made a new post", target=post, action_object=post.workgroup)


def review_request_created(review_request, requester, registrar):
    notify.send(requester, recipient=registrar, verb="requested concept review", target=review_request)


def review_request_updated(review_request, requester, reviewer):
    if reviewer:
        notify.send(reviewer, recipient=requester, verb="concept was reviewed", target=review_request)
    else:
        # Maybe it was auto reviewed, or updated manually?
        notify.send(review_request, recipient=requester, verb="concept was reviewed", target=review_request)
