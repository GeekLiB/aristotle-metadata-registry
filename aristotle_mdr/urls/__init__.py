from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth.views import password_reset
from django.views.generic.base import RedirectView
from aristotle_mdr.views.user_pages import friendly_redirect_login

admin.autodiscover()

urlpatterns = [
    url(r'^', include('aristotle_mdr.urls.base')),
    url(r'^', include('aristotle_mdr.urls.aristotle', app_name="aristotle_mdr", namespace="aristotle")),
    url(r'^ac/', include('aristotle_mdr.contrib.autocomplete.urls', namespace="aristotle-autocomplete")),
]


if 'aristotle_mdr.contrib.browse' in settings.INSTALLED_APPS:
    urlpatterns.append(url(r'^browse/', include('aristotle_mdr.contrib.browse.urls')))

if 'aristotle_mdr.contrib.help' in settings.INSTALLED_APPS:
    urlpatterns.append(url(r'^help/', include('aristotle_mdr.contrib.help.urls', app_name="aristotle_help", namespace="aristotle_help")))

if 'aristotle_mdr.contrib.links' in settings.INSTALLED_APPS:
    urlpatterns.append(url(r'^', include('aristotle_mdr.contrib.links.urls', app_name="aristotle_mdr_links", namespace="aristotle_links")))

if 'aristotle_mdr.contrib.self_publish' in settings.INSTALLED_APPS:
    urlpatterns.append(url(r'^publish/', include('aristotle_mdr.contrib.self_publish.urls', app_name="aristotle_self_publish", namespace="aristotle_self_publish")))

if 'aristotle_mdr.contrib.slots' in settings.INSTALLED_APPS:
    urlpatterns.append(url(r'^', include('aristotle_mdr.contrib.slots.urls', app_name="aristotle_slots", namespace="aristotle_slots")))

if 'aristotle_mdr.contrib.identifiers' in settings.INSTALLED_APPS:
    urlpatterns.append(url(r'^', include('aristotle_mdr.contrib.identifiers.urls', app_name="aristotle_mdr_identifiers", namespace="aristotle_identifiers")))
urlpatterns.append(url(r'^', include('aristotle_mdr.contrib.healthcheck.urls', app_name="aristotle_mdr_hb", namespace="aristotle_hb")))

# This is only for dev work, so we can skip it.
if settings.DEBUG:  # pragma: no cover
    from django.conf import settings
    from django.conf.urls.static import static
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler403 = 'aristotle_mdr.views.unauthorised'
