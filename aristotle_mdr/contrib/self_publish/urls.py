from django.conf.urls import url
from aristotle_mdr.contrib.self_publish import views


urlpatterns = [
    url(r'^item/(?P<iid>\d+)/?$', views.PublishMetadataFormView.as_view(), name='publish_metadata'),
]
