"""base URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from crm.views import ContactListView, ContactDetailView, ContactCreateView, ContactUpdateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("contacts/", ContactListView.as_view(), name='contact-list'),
    path("contacts/create/", ContactCreateView.as_view(), name='contact-create'),
    path("contacts/<slug:slug>/", ContactDetailView.as_view(), name='contact-detail'),
    path("contacts/<slug:slug>/update/", ContactUpdateView.as_view(), name='contact-update'),
]
