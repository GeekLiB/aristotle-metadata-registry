from django.conf.urls import url
from aristotle_mdr.contrib.healthcheck import views


urlpatterns = [
    url(r'^healthz/?$', views.heartbeat, name='health'),
]
