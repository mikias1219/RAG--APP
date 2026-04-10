from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("chat/", views.chat, name="chat"),
    path("upload/", views.upload, name="upload"),
    path("health/", views.health, name="health"),
]
