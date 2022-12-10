"""Muberz URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin

# from Muberz import api_base
from django.conf.urls.static import static
from django.views.generic import TemplateView

from dashboard.views import Error404View

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^api/', include('api_base.urls', namespace='rest_framework')),
    # DASHBOARD URLS
    url(r'^dashboard/', include('dashboard.urls', namespace='dashboard')),
    url(r'^404/$', Error404View.as_view(), name='404'),
    url('privacy-policy/', TemplateView.as_view(template_name="dashboard/Privacy_policy_Muberz.html")),
]
