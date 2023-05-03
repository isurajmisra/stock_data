
from django.urls import path

from . import views

urlpatterns = [
    path('/', views.home, name="home"),
    path('option_chart/', views.get_chart, name="option_chart"),
    path('api/get_intraday_data/', views.get_intraday_data, name="get_intraday_data"),
    path('api/api_get_data/', views.api_get_data, name="api_get_data"),

]


