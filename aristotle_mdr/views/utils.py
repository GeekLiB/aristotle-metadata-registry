from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.db.models.functions import Lower


paginate_sort_opts = {
    "mod_asc": ["modified"],
    "mod_desc": ["-modified"],
    "cre_asc": ["created"],
    "cre_desc": ["-created"],
    "name_asc": [Lower("name").asc()],
    "name_desc": [Lower("name").desc()],
}


@login_required
def paginated_list(request, items, template, extra_context={}):
    if hasattr(items, 'select_subclasses'):
        items = items.select_subclasses()
    sort_by=request.GET.get('sort', "mod_desc")
    if sort_by not in paginate_sort_opts.keys():
        sort_by="mod_desc"

    paginator = Paginator(
        items.order_by(*paginate_sort_opts.get(sort_by)),
        request.GET.get('pp', 20)  # per page
    )

    page = request.GET.get('page')
    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        items = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        items = paginator.page(paginator.num_pages)
    context = {
        'sort': sort_by,
        'page': items,
        }
    context.update(extra_context)
    return render(request, template, context)


@login_required
def paginated_reversion_list(request, items, template, extra_context={}):

    paginator = Paginator(
        items,
        request.GET.get('pp', 20)  # per page
    )

    page = request.GET.get('page')
    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        items = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        items = paginator.page(paginator.num_pages)
    context = {
        'page': items,
        }
    context.update(extra_context)
    return render(request, template, context)


paginate_workgroup_sort_opts = {
    "users": ("user_count", lambda qs: qs.annotate(user_count=Count('viewers'))),
    "items": ("item_count", lambda qs: qs.annotate(item_count=Count('items'))),
    "name": "name",
}


@login_required
def paginated_workgroup_list(request, workgroups, template, extra_context={}):
    sort_by=request.GET.get('sort', "name_desc")
    try:
        sorter, direction = sort_by.split('_')
        if sorter not in paginate_workgroup_sort_opts.keys():
            sorter="name"
            sort_by = "name_desc"
        direction = {'asc': '', 'desc': '-'}.get(direction, '')
    except:
        sorter, direction = 'name', ''

    opts = paginate_workgroup_sort_opts.get(sorter)
    qs = workgroups

    try:
        sort_field, extra = opts
        qs = extra(qs)
    except:
        sort_field = opts

    qs = qs.order_by(direction + sort_field)
    paginator = Paginator(
        qs,
        request.GET.get('pp', 20)  # per page
    )

    page = request.GET.get('page')
    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        items = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        items = paginator.page(paginator.num_pages)
    context = {
        'sort': sort_by,
        'page': items,
        }
    context.update(extra_context)
    return render(request, template, context)


def get_concept_redirect_or_404(get_item_perm, request, iid, objtype=None):
    if objtype is None:
        from aristotle_mdr.models import _concept
        objtype = _concept

    from aristotle_mdr.contrib.redirect.exceptions import Redirect

    item = get_item_perm(objtype, request.user, iid)
    if not item:
        if request.user.is_anonymous():
            raise Redirect(reverse('friendly_login') + '?next=%s' % request.path)
        else:
            raise PermissionDenied
    else:
        return item


def workgroup_item_statuses(workgroup):
    from aristotle_mdr.models import STATES

    raw_counts = workgroup.items.filter(
        Q(statuses__until_date__gte=timezone.now()) |
        Q(statuses__until_date__isnull=True)
    ).values_list('statuses__state').annotate(num=Count('id'))

    counts = []
    for state, count in raw_counts:
        if state is None:
            state = _("Not registered")
        else:
            state = STATES[state]
        counts.append((state, count))
    return counts


def generate_visibility_matrix(user):
    matrix={}

    from aristotle_mdr.models import STATES

    for ra in user.profile.registrarAuthorities:
        ra_matrix = {'name': ra.name, 'states': {}}
        for s, _ in STATES:
            if s > ra.public_state:
                ra_matrix['states'][s] = "public"
            elif s > ra.locked_state:
                ra_matrix['states'][s] = "locked"
            else:
                ra_matrix['states'][s] = "hidden"
        matrix[ra.id] = ra_matrix
    return matrix
