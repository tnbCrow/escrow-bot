from django.contrib import admin
from django.urls import path

from rest_framework.routers import DefaultRouter

from escrow.urls import router as escrow_router

urlpatterns = [
    path('admin/', admin.site.urls),
]

router = DefaultRouter(trailing_slash=False)
router.registry.extend(escrow_router.registry)
urlpatterns += router.urls
