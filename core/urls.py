from django.urls import path

from . import views

urlpatterns = [
    path('', views.get_stock_data, name="get_data"),
    path('api/get_intraday_data/', views.get_intraday_data, name="get_intraday_data"),

]

