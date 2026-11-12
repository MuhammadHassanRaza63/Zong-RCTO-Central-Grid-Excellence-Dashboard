from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('grid/', include('grid_report.urls')),   # Grid Excellence module
    path('', include('dashboard.urls')),
]
