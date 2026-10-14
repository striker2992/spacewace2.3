from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard") if hasattr(views, "dashboard") else path("", views.HomeView.as_view(), name="dashboard") if hasattr(views, "HomeView") else path("", views.IndexView.as_view(), name="dashboard") if hasattr(views, "IndexView") else path("", views.login_view, name="dashboard"),
]