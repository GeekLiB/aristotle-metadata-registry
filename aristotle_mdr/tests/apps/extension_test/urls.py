from django.conf.urls import include, url
from aristotle_mdr.contrib.generic.views import GenericAlterManyToManyView

from aristotle_mdr.views import views
from aristotle_mdr.forms.search import PermissionSearchForm

from haystack.views import search_view_factory
from haystack.query import SearchQuerySet


urlpatterns = [
    url(r'^', include('aristotle_mdr.urls')),
    url(r'^extension_test/', include('extension_test.extension_urls', app_name="extension_test", namespace="extension_test")),
    url(
        r'^fail_search/?',
        search_view_factory(
            view_class=views.PermissionSearchView,
            template='search/search.html',
            searchqueryset= SearchQuerySet(),
            form_class=PermissionSearchForm
            ),
        name='fail_search'
    ),
]
