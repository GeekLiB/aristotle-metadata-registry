import notifications.urls

from django.conf import settings
from django.conf.urls import include, url
from django.contrib.auth import views
from django.contrib import admin
from django.views.generic.base import RedirectView
from aristotle_mdr.views.user_pages import friendly_redirect_login

admin.autodiscover()

urlpatterns = [
    url(r'^login/?$', friendly_redirect_login, name='friendly_login'),
    url(r'^logout/?$', views.logout, {'next_page': '/'}, name='logout'),
    url(r'^django/admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^django/admin/', include(admin.site.urls)),
    url(r'^ckeditor/', include('aristotle_mdr.urls.ckeditor_uploader')),
    url(r'^account/notifications/', include(notifications.urls, namespace="notifications")),
    url(r'^account/password/reset/$', views.password_reset),  # , {'template_name': 'my_templates/password_reset.html'}
    url(r'^account/password/reset_done/$', views.password_reset),  # , {'template_name': 'my_templates/password_reset.html'}
    url(
        r'^user/password/reset/$',
        views.password_reset,
        {'post_reset_redirect': '/user/password/reset/done/'},
        name="password_reset"
    ),
    url(
        r'^user/password/reset/done/$',
        views.password_reset_done,
        name="password_reset_done"
    ),
    url(r'^user/password/reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        views.password_reset_confirm,
        {'post_reset_redirect': '/user/password/done/'},
        name='password_reset_confirm',),
    url(r'^user/password/done/$',
        views.password_reset_complete),

    url(r'^account/password/?$', RedirectView.as_view(url='account/home/', permanent=True)),
    url(r'^account/password/change/?$', views.password_change, name='password_change'),
    url(r'^account/password/change/done/?$', views.password_change_done, name='password_change_done'),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
