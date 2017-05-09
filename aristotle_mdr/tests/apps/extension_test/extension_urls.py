from django.conf.urls import url
from aristotle_mdr.contrib.generic.views import GenericAlterManyToManyView

from extension_test import views
from extension_test import models

urlpatterns = [
    url(r'^about/(?P<template>.+)/?$', views.DynamicTemplateView.as_view(), name="about"),
    url(r'^questionnaire/(?P<iid>\d+)/add_question/?$',
        GenericAlterManyToManyView.as_view(
            model_base = models.Questionnaire,
            model_to_add = models.Question,
            model_base_field = 'questions'
        ), name='questionnaire_add_question'),
]
