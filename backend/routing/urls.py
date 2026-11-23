"""
Routing App URL Configuration.
"""

from django.urls import path
from .views import (
    AnalyzeRoutesView,
    CompareRoutesView,
    RoutesHealthCheckView,
    WeatherHealthCheckView,
)

urlpatterns = [
    path('routes/analyze/', AnalyzeRoutesView.as_view(), name='routes-analyze'),
    path('routes/compare/', CompareRoutesView.as_view(), name='routes-compare'),
    path('routes/health/', RoutesHealthCheckView.as_view(), name='routes-health'),
    path('weather/health/', WeatherHealthCheckView.as_view(), name='weather-health'),
]
