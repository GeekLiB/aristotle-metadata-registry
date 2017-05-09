from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.forms import model_to_dict
from django.template.defaultfilters import slugify
from django.utils.encoding import force_text
from django.utils.module_loading import import_string
from django.utils.text import get_text_list
from django.utils.translation import ugettext as _


def concept_to_dict(obj):
    """
    A replacement for the ```django.form.model_to_dict`` that includes additional
    ``ManyToManyFields``, but removes certain concept fields.
    """

    excluded_fields='_concept_ptr version workgroup pk id supersedes superseded_by _is_public _is_locked'.split()
    concept_dict = model_to_dict(
        obj,
        fields=[field.name for field in obj._meta.fields if field.name not in excluded_fields],
        exclude=excluded_fields
    )
    return concept_dict


def concept_to_clone_dict(obj):
    """
    An extension of ``aristotle_mdr.utils.concept_to_dict`` that adds a 'clone'
    suffix to the name when cloning an item.
    """

    from django.utils.translation import ugettext  # Do at run time because reasons
    clone_dict = concept_to_dict(obj)
    # Translators: The '(clone)' prefix is a noun, indicating an object is a clone of another - for example "Person-Sex" compared to "Person-Sex (clone)"
    clone_dict['name'] = clone_dict['name'] + ugettext(u" (clone)")
    return clone_dict


def get_download_template_path_for_item(item, download_type, subpath=''):
    app_label = item._meta.app_label
    model_name = item._meta.model_name
    if subpath:
        template = "%s/downloads/%s/%s/%s.html" % (app_label, download_type, subpath, model_name)
    else:
        template = "%s/downloads/%s/%s.html" % (app_label, download_type, model_name)

    from django.template.loader import get_template
    from django.template import TemplateDoesNotExist
    try:
        get_template(template)
    except TemplateDoesNotExist:
        # This is ok. If a template doesn't exists pass a default one
        # Maybe in future log an error?
        template = "%s/downloads/%s/%s/%s.html" % ("aristotle_mdr", download_type, subpath, "managedContent")
    return template


def url_slugify_concept(item):
    item = item.item
    slug = slugify(item.name)[:50]
    if not slug:
        slug = "--"
    return reverse(
        "aristotle:item",
        kwargs={'iid': item.pk, 'model_slug': item._meta.model_name, 'name_slug': slug}
    )


def url_slugify_workgroup(workgroup):
    slug = slugify(workgroup.name)[:50]
    if not slug:
        slug = "--"
    return reverse(
        "aristotle:workgroup",
        kwargs={'iid': workgroup.pk, 'name_slug': slug}
    )


def url_slugify_registration_authoritity(ra):
    slug = slugify(ra.name)[:50]
    if not slug:
        slug = "--"
    return reverse(
        "aristotle:registrationAuthority",
        kwargs={'iid': ra.pk, 'name_slug': slug}
    )


def url_slugify_organization(org):
    slug = slugify(org.name)[:50]
    if not slug:
        slug = "--"
    return reverse(
        "aristotle:organization",
        kwargs={'iid': org.pk, 'name_slug': slug}
    )


def construct_change_message(request, form, formsets):
    """
    Construct a change message from a changed object.
    """
    change_message = []
    if form and form.changed_data:
        change_message.append(_('Changed %s.') % get_text_list(form.changed_data, _('and')))

    if formsets:
        for formset in formsets:
            for added_object in formset.new_objects:
                # Translators: A message in the version history of an item saying that an object with the name (name) of the type (object) has been created in the registry.
                change_message.append(_('Added %(name)s "%(object)s".')
                                      % {'name': force_text(added_object._meta.verbose_name),
                                         'object': force_text(added_object)})
            for changed_object, changed_fields in formset.changed_objects:
                # Translators: A message in the version history of an item saying that an object with the name (name) of the type (object) has been changed in the registry.
                change_message.append(_('Changed %(list)s for %(name)s "%(object)s".')
                                      % {'list': get_text_list(changed_fields, _('and')),
                                         'name': force_text(changed_object._meta.verbose_name),
                                         'object': force_text(changed_object)})
            for deleted_object in formset.deleted_objects:
                # Translators: A message in the version history of an item saying that an object with the name (name) of the type (object) has been deleted from the registry.
                change_message.append(_('Deleted %(name)s "%(object)s".')
                                      % {'name': force_text(deleted_object._meta.verbose_name),
                                         'object': force_text(deleted_object)})
    change_message = ' '.join(change_message)
    return change_message or _('No fields changed.')


def get_concepts_for_apps(app_labels):
    from django.contrib.contenttypes.models import ContentType
    from aristotle_mdr import models as MDR
    models = ContentType.objects.filter(app_label__in=app_labels).all().order_by('model')
    concepts = [
        m
        for m in models
        if m.model_class() and issubclass(m.model_class(), MDR._concept) and
        not m.model.startswith("_")
    ]
    return concepts


# "There are only two hard problems in Computer Science: cache invalidation, naming things and off-by-one errors"
def cache_per_item_user(ttl=None, prefix=None, cache_post=False):
    '''
    Modified from: https://djangosnippets.org/snippets/2524/
    '''

    def decorator(function):
        def apply_cache(request, *args, **kwargs):
            # Gera a parte do usuario que ficara na chave do cache
            if request.user.is_anonymous():
                user = 'anonymous'
            else:
                user = request.user.id

            iid = kwargs['iid']

            if prefix:  # pragma no cover - we don't use this
                CACHE_KEY = '%s_%s_%s' % (prefix, user, iid)
            else:
                CACHE_KEY = 'view_cache_%s_%s_%s' % (function.__name__, user, iid)

            if not cache_post and request.method == 'POST':
                can_cache = False
            else:
                can_cache = True

            from aristotle_mdr.models import _concept
            import datetime
            from django.utils import timezone

            if 'nocache' not in request.GET.keys():
                can_cache = False

            # If the item was modified in the last 15 seconds, don't use cache
            recently = timezone.now() - datetime.timedelta(seconds=15)
            if _concept.objects.filter(id=iid, modified__gte=recently).exists():
                can_cache = False

            if can_cache:
                response = cache.get(CACHE_KEY, None)
            else:
                response = None

            if not response:
                response = function(request, *args, **kwargs)
                if can_cache:
                    cache.set(CACHE_KEY, response, ttl)
            return response
        return apply_cache
    return decorator


def fetch_aristotle_settings():
    if hasattr(settings, 'ARISTOTLE_SETTINGS_LOADER'):
        return import_string(getattr(settings, 'ARISTOTLE_SETTINGS_LOADER'))()
    return getattr(settings, 'ARISTOTLE_SETTINGS', {})
