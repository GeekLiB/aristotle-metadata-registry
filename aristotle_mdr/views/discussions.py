from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.utils.translation import ugettext_lazy as _

from aristotle_mdr import models as MDR
from aristotle_mdr import forms as MDRForms
from aristotle_mdr import perms


@login_required
def all(request):
    # Show all discussions for all of a users workgroups
    page = render(request, "aristotle_mdr/discussions/all.html", {
        'discussions': request.user.profile.discussions
        })
    return page


@login_required
def workgroup(request, wgid):
    wg = get_object_or_404(MDR.Workgroup, pk=wgid)
    if not perms.user_in_workgroup(request.user, wg):
        raise PermissionDenied
    # Show all discussions for a workgroups
    page = render(request, "aristotle_mdr/discussions/workgroup.html", {
        'workgroup': wg,
        'discussions': wg.discussions.all()  # MDR.DiscussionPost.objects.filter(workgroup=wg)
        })
    return page


@login_required
def post(request, pid):
    post = get_object_or_404(MDR.DiscussionPost, pk=pid)
    if not perms.user_in_workgroup(request.user, post.workgroup):
        raise PermissionDenied
    # Show all discussions for a workgroups
    comment_form = MDRForms.discussions.CommentForm(initial={'post': pid})
    page = render(request, "aristotle_mdr/discussions/post.html", {
        'workgroup': post.workgroup,
        'post': post,
        'comment_form': comment_form
        })
    return page


@login_required
def toggle_post(request, pid):
    post = get_object_or_404(MDR.DiscussionPost, pk=pid)
    if not perms.user_can_alter_post(request.user, post):
        raise PermissionDenied
    post.closed = not post.closed
    post.save()
    return HttpResponseRedirect(reverse("aristotle:discussionsPost", args=[post.pk]))


@login_required
def new(request):
    if request.method == 'POST':  # If the form has been submitted...
        form = MDRForms.discussions.NewPostForm(request.POST, user=request.user)  # A form bound to the POST data
        if form.is_valid():
            # process the data in form.cleaned_data as required
            new = MDR.DiscussionPost(
                workgroup=form.cleaned_data['workgroup'],
                title=form.cleaned_data['title'],
                body=form.cleaned_data['body'],
                author=request.user,
            )
            new.save()
            new.relatedItems = form.cleaned_data['relatedItems']
            return HttpResponseRedirect(reverse("aristotle:discussionsPost", args=[new.pk]))
    else:
        initial = {}
        if request.GET.get('workgroup'):
            if request.user.profile.myWorkgroups.filter(id=request.GET.get('workgroup')).exists():
                initial={'workgroup': request.GET.get('workgroup')}
            else:
                # If a user tries to navigate to a page to post to a workgroup they aren't in, redirect them to the regular post page.
                return HttpResponseRedirect(reverse("aristotle:discussionsNew"))
            if request.GET.getlist('item'):
                workgroup = request.user.profile.myWorkgroups.get(id=request.GET.get('workgroup'))
                items = request.GET.getlist('item')
                initial.update({'relatedItems': workgroup.items.filter(id__in=items)})

        form = MDRForms.discussions.NewPostForm(user=request.user, initial=initial)
    return render(request, "aristotle_mdr/discussions/new.html", {"form": form})


@login_required
def new_comment(request, pid):
    post = get_object_or_404(MDR.DiscussionPost, pk=pid)
    if not perms.user_in_workgroup(request.user, post.workgroup):
        raise PermissionDenied
    if post.closed:
        messages.error(request, _('This post is closed. Your comment was not added.'))
        return HttpResponseRedirect(reverse("aristotle:discussionsPost", args=[post.pk]))
    if request.method == 'POST':
        form = MDRForms.discussions.CommentForm(request.POST)
        if form.is_valid():
            new = MDR.DiscussionComment(
                post=post,
                body=form.cleaned_data['body'],
                author=request.user,
            )
            new.save()
            return HttpResponseRedirect(reverse("aristotle:discussionsPost", args=[new.post.pk]) + "#comment_%s" % new.id)
        else:
            return render(request, "aristotle_mdr/discussions/new.html", {"form": form})
    else:
        # It makes no sense to "GET" this comment, so push them back to the discussion
        return HttpResponseRedirect(reverse("aristotle:discussionsPost", args=[post.pk]))


@login_required
def delete_comment(request, cid):
    comment = get_object_or_404(MDR.DiscussionComment, pk=cid)
    post = comment.post
    if not perms.user_can_alter_comment(request.user, comment):
        raise PermissionDenied
    comment.delete()
    return HttpResponseRedirect(reverse("aristotle:discussionsPost", args=[post.pk]))


@login_required
def delete_post(request, pid):
    post = get_object_or_404(MDR.DiscussionPost, pk=pid)
    workgroup = post.workgroup
    if not perms.user_can_alter_post(request.user, post):
        raise PermissionDenied
    post.comments.all().delete()
    post.delete()
    return HttpResponseRedirect(reverse("aristotle:discussionsWorkgroup", args=[workgroup.pk]))


@login_required
def edit_comment(request, cid):
    comment = get_object_or_404(MDR.DiscussionComment, pk=cid)
    post = comment.post
    if not perms.user_can_alter_comment(request.user, comment):
        raise PermissionDenied
    if request.method == 'POST':
        form = MDRForms.discussions.CommentForm(request.POST)
        if form.is_valid():
            comment.body = form.cleaned_data['body']
            comment.save()
            return HttpResponseRedirect(reverse("aristotle:discussionsPost", args=[comment.post.pk]) + "#comment_%s" % comment.id)
    else:
        form = MDRForms.discussions.CommentForm(instance=comment)

    return render(request, "aristotle_mdr/discussions/edit_comment.html", {
        'post': post,
        'comment_form': form})


@login_required
def edit_post(request, pid):
    post = get_object_or_404(MDR.DiscussionPost, pk=pid)
    if not perms.user_can_alter_post(request.user, post):
        raise PermissionDenied
    if request.method == 'POST':  # If the form has been submitted...
        form = MDRForms.discussions.EditPostForm(request.POST)  # A form bound to the POST data
        if form.is_valid():
            # process the data in form.cleaned_data as required
            post.title = form.cleaned_data['title']
            post.body = form.cleaned_data['body']
            post.save()
            post.relatedItems = form.cleaned_data['relatedItems']
            return HttpResponseRedirect(reverse("aristotle:discussionsPost", args=[post.pk]))
    else:
        form = MDRForms.discussions.EditPostForm(instance=post)
    return render(request, "aristotle_mdr/discussions/edit.html", {"form": form, 'post': post})
