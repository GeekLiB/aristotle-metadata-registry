from channels import Group
from aristotle_mdr import models as MDR
from aristotle_mdr import messages
from aristotle_mdr.contrib.channels.utils import safe_object


def concept_saved(message):
    instance = safe_object(message)
    if not instance:
        return

    for p in instance.favourited_by.all():
        if sorted(message['changed_fields']) == ['modified', 'superseded_by_id']:
            messages.favourite_superseded(recipient=p.user, obj=instance)
        else:
            messages.favourite_updated(recipient=p.user, obj=instance)

    for status in instance.current_statuses().all():
        for registrar in status.registrationAuthority.registrars.all():
            if sorted(message['changed_fields']) == ['modified', 'superseded_by_id']:
                messages.registrar_item_superseded(recipient=registrar, obj=instance)

    if instance.workgroup:
        for user in instance.workgroup.viewers.all():
            if message['created']:
                messages.workgroup_item_new(recipient=user, obj=instance)
            else:
                messages.workgroup_item_updated(recipient=user, obj=instance)
    try:
        # This will fail during first load, and if admins delete aristotle.
        system = User.objects.get(username="aristotle")
        for post in instance.relatedDiscussions.all():
            DiscussionComment.objects.create(
                post=post,
                body='The item "{name}" (id:{iid}) has been changed.\n\n\
                    <a href="{url}">View it on the main site.</a>.'.format(
                    name=instance.name,
                    iid=instance.id,
                    url=reverse("aristotle:item", args=[instance.id])
                ),
                author=system,
            )
    except:
        pass


def new_comment_created(message, **kwargs):
    comment = safe_object(message)
    if comment:
        messages.new_comment_created(comment)


def new_post_created(message, **kwargs):
    post = safe_object(message)

    if post:
        for user in post.workgroup.members.all():
            if user != post.author:
                messages.new_post_created(post, user)


def status_changed(message, **kwargs):
    new_status = safe_object(message)
    concept = new_status.concept

    for status in concept.current_statuses().all():
        for registrar in status.registrationAuthority.registrars.all():
            if concept.statuses.filter(registrationAuthority=new_status.registrationAuthority).count() <= 1:
                # 0 or 1 because the transaction may not be complete yet
                messages.registrar_item_registered(recipient=registrar, obj=concept)
            else:
                messages.registrar_item_changed_status(recipient=registrar, obj=concept)
