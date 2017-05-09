from django.conf.urls import url
from aristotle_mdr.contrib.slots import views


urlpatterns = [
    url(r'^slots/similar/(?P<slot_name>.+)/?$', views.SimilarSlotsView.as_view(), name='similar_slots'),
]
