"""
API Views for Weather-Aware Truck Routing.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests

from .serializers import AnalyzeRouteRequestSerializer
from .services import analyze_weather_truck_routes, geocode_location


class AnalyzeRoutesView(APIView):
    """
    POST /api/routes/analyze/
    Analyzes weather conditions along three alternative driving corridors
    and generates lexicographical safety recommendations.
    """
    def post(self, request):
        serializer = AnalyzeRouteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "status": "error",
                    "errors": serializer.errors,
                    "message": "Validation failed for route analysis request."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        try:
            result = analyze_weather_truck_routes(
                origin_query=data["origin"],
                destination_query=data["destination"],
                departure_time_iso=data["departure_time"],
                load_weight_lb=data["load_weight_lb"],
                sampling_interval_miles=float(data["sampling_interval_miles"]),
                user_timezone_offset_minutes=data.get("timezone_offset_minutes"),
                allow_simulated_fallback=data.get("allow_simulated_fallback", False),
            )
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as ve:
            return Response(
                {
                    "status": "error",
                    "message": str(ve)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    "status": "error",
                    "message": f"An unexpected error occurred during route analysis: {str(e)}"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CompareRoutesView(APIView):
    """
    POST /api/routes/compare/
    Lightweight route comparison endpoint.
    """
    def post(self, request):
        return AnalyzeRoutesView().post(request)


class RoutesHealthCheckView(APIView):
    """
    GET /api/routes/health/
    Health check for routing and backend services.
    """
    def get(self, request):
        return Response(
            {
                "status": "healthy",
                "service": "weather-aware-truck-routing",
                "routing_engines": ["OSRM Smart Corridor", "OpenRouteService", "Highway Corridor Fallback"],
                "geocoding_engine": "OpenStreetMap Nominatim / Photon",
            },
            status=status.HTTP_200_OK
        )


class WeatherHealthCheckView(APIView):
    """
    GET /api/weather/health/
    Health check for Open-Meteo weather API connection.
    """
    def get(self, request):
        try:
            resp = requests.get(
                "https://api.open-meteo.com/v1/forecast?latitude=40.71&longitude=-74.00&hourly=temperature_2m&forecast_days=1",
                timeout=4
            )
            if resp.status_code == 200:
                return Response(
                    {
                        "status": "healthy",
                        "provider": "Open-Meteo",
                        "response_time_ms": resp.elapsed.total_seconds() * 1000,
                    },
                    status=status.HTTP_200_OK
                )
            return Response(
                {"status": "degraded", "provider": "Open-Meteo", "http_status": resp.status_code},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            return Response(
                {"status": "unavailable", "provider": "Open-Meteo", "error": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
