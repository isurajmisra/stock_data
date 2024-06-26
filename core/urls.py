
from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('strike_price/', views.get_chart, name="option_chart"),
    path('strike_prices/', views.get_strike, name="strike_price"),
    path('api/get_intraday_data/', views.get_intraday_data, name="get_intraday_data"),
    path('api/api_get_data/', views.api_get_data, name="api_get_data"),
    path('api/api_get_strike_data/', views.get_strike_price_data, name="api_get_strike_data"),
]


