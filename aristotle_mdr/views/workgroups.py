from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.template.defaultfilters import slugify

from aristotle_mdr import models as MDR
from aristotle_mdr import forms as MDRForms
from aristotle_mdr.views.utils import paginated_list, workgroup_item_statuses
from aristotle_mdr.perms import user_in_workgroup, user_is_workgroup_manager


@login_required
def workgroup(request, iid, name_slug):
    wg = get_object_or_404(MDR.Workgroup, pk=iid)
    if not slugify(wg.name).startswith(str(name_slug)):
        return redirect(wg.get_absolute_url())
    if not user_in_workgroup(request.user, wg):
        raise PermissionDenied
    renderDict = {
        "item": wg,
        "workgroup": wg,
        "user_is_admin": user_is_workgroup_manager(request.user, wg),
        "counts": workgroup_item_statuses(wg)
    }
    renderDict['recent'] = MDR._concept.objects.filter(workgroup=iid).select_subclasses().order_by('-modified')[:5]
    page = render(request, wg.template, renderDict)
    return page


@login_required
def items(request, iid):
    wg = get_object_or_404(MDR.Workgroup, pk=iid)
    if not user_in_workgroup(request.user, wg):
        raise PermissionDenied
    items = MDR._concept.objects.filter(workgroup=iid).select_subclasses()
    context = {
        "item": wg,
        "workgroup": wg,
        "user_is_admin": user_is_workgroup_manager(request.user, wg),
        "select_all_list_queryset_filter": 'workgroup__pk=%s' % wg.pk
    }
    return paginated_list(request, items, "aristotle_mdr/workgroupItems.html", context)


@login_required
def members(request, iid):
    wg = get_object_or_404(MDR.Workgroup, pk=iid)
    renderDict = {"item": wg, "workgroup": wg, "user_is_admin": user_is_workgroup_manager(request.user, wg)}
    if not user_in_workgroup(request.user, wg):
        raise PermissionDenied
    return render(request, "aristotle_mdr/workgroupMembers.html", renderDict)


@login_required
def remove_role(request, iid, role, userid):
    workgroup = get_object_or_404(MDR.Workgroup, pk=iid)
    if not (workgroup and user_is_workgroup_manager(request.user, workgroup)):
        raise PermissionDenied
    try:
        user = User.objects.get(id=userid)
        workgroup.removeRoleFromUser(role, user)
    except:
        pass
    return HttpResponseRedirect(reverse("aristotle:workgroupMembers", args=[workgroup.pk]))


@login_required
def archive(request, iid):
    workgroup = get_object_or_404(MDR.Workgroup, pk=iid)
    if not (workgroup and user_is_workgroup_manager(request.user, workgroup)):
        raise PermissionDenied
    if request.method == 'POST':  # If the form has been submitted...
        workgroup.archived = not workgroup.archived
        workgroup.save()
        return HttpResponseRedirect(workgroup.get_absolute_url())
    else:
        return render(request, "aristotle_mdr/actions/archive_workgroup.html", {"item": workgroup})


@login_required
def add_members(request, iid):
    workgroup = get_object_or_404(MDR.Workgroup, pk=iid)
    if not (workgroup and user_is_workgroup_manager(request.user, workgroup)):
        raise PermissionDenied
    if request.method == 'POST':  # If the form has been submitted...
        form = MDRForms.workgroups.AddMembers(request.POST)  # A form bound to the POST data
        if form.is_valid():
            # process the data in form.cleaned_data as required
            users = form.cleaned_data['users']
            roles = form.cleaned_data['roles']
            for user in users:
                for role in roles:
                    workgroup.giveRoleToUser(role, user)
            return HttpResponseRedirect(reverse("aristotle:workgroupMembers", args=[workgroup.pk]))
    else:
        form = MDRForms.workgroups.AddMembers(initial={'roles': request.GET.getlist('role')})

    return render(
        request,
        "aristotle_mdr/actions/addWorkgroupMember.html",
        {
            "item": workgroup,
            "form": form,
            "role": request.GET.get('role')
        }
    )


@login_required
def leave(request, iid):
    workgroup = get_object_or_404(MDR.Workgroup, pk=iid)
    if not (workgroup and request.user in workgroup.members):
        raise PermissionDenied

    if request.method == 'POST':  # If the form has been submitted...
        workgroup.removeUser(request.user)
        return HttpResponseRedirect(reverse("aristotle:userHome"))

    return render(
        request,
        "aristotle_mdr/actions/workgroup_leave.html",
        {
            "item": workgroup,
        }
    )
