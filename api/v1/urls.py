from django.urls import path, re_path
from .views import GetStatInfo, GetData, GetVlan, GetVlanByDesc

# /api/v1/

urlpatterns = [
    path('info/', GetStatInfo.as_view()),
    re_path('(?P<type_>interfaces|vlans)/', GetData.as_view()),
    path('vlan/<int:vid>', GetVlan.as_view()),
    path('vlan/desc/<desc>', GetVlanByDesc.as_view()),
]
