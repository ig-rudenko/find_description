from django.urls import path
from find_desc import views

urlpatterns = [
    path('', views.home, name='home'),
    path('find', views.find_as_str, name='find'),
    path('vlantraceroute', views.get_vlan, name='vlantraceroute')
]
