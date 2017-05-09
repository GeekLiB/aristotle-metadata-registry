from django.conf.urls import url
from aristotle_mdr.contrib.identifiers.views import scoped_identifier_redirect


urlpatterns = [
    url(r'^identifier/(?P<ns_prefix>.+)/(?P<iid>.+)/?$', scoped_identifier_redirect, name='scoped_identifier_redirect'),
]
