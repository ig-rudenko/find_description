from django.urls import path, include

# /api/

urlpatterns = [
    path('v1/', include('api.v1.urls'))
]