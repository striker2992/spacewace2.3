from django.urls import path
from . import views

app_name = "clientes"

urlpatterns = [
    path("registro/", views.RegistroView.as_view(), name="registro") if hasattr(views, "RegistroView") else path("", views.RegistroView.as_view(), name="registro"),
]