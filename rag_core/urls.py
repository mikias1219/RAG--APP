from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.landing, name="home"),
    path("health/", views.health, name="health"),
    path("register/", views.register, name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="rag_core/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("app/", views.dashboard, name="dashboard"),
    path("app/organization/", views.organization_settings, name="organization_settings"),
    path("app/collections/new/", views.collection_create, name="collection_create"),
    path("app/collections/<int:pk>/", views.collection_detail, name="collection_detail"),
    path(
        "app/collections/<int:pk>/documents/<int:doc_pk>/delete/",
        views.document_delete,
        name="document_delete",
    ),
    path("app/chat/", views.chat, name="chat"),
]
