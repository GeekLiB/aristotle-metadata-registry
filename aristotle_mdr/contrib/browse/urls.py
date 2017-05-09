from django.conf.urls import url

from aristotle_mdr.contrib.browse import views

urlpatterns = [
    url(r'^(?P<app>[a-zA-Z_]+)/(?P<model>[a-zA-Z_]+)/?', views.BrowseConcepts.as_view(), name='browse_concepts'),
    url(r'^(?P<app>[a-zA-Z_]+)/?', views.BrowseModels.as_view(), name='browse_models'),
    url(r'^$', views.BrowseApps.as_view(), name='browse_apps'),
]
