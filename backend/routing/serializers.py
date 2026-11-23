"""
Serializers for Weather-Aware Truck Routing API.
"""

from rest_framework import serializers
from datetime import datetime


class AnalyzeRouteRequestSerializer(serializers.Serializer):
    origin = serializers.CharField(
        required=True,
        max_length=250,
        trim_whitespace=True,
        help_text="Origin location, e.g. 'Chicago, IL'"
    )
    destination = serializers.CharField(
        required=True,
        max_length=250,
        trim_whitespace=True,
        help_text="Destination location, e.g. 'New York, NY'"
    )
    departure_time = serializers.CharField(
        required=True,
        help_text="Departure timestamp in ISO 8601 format, e.g. '2026-11-24T08:00' or '2026-11-24T08:00:00-05:00'"
    )
    load_weight_lb = serializers.FloatField(
        required=True,
        min_value=0.0,
        max_value=120000.0,
        help_text="Truck load weight in pounds (0 to 120,000 lb)"
    )
    sampling_interval_miles = serializers.ChoiceField(
        choices=[10, 25, 50],
        default=25,
        help_text="Weather sampling interval along route: 10, 25, or 50 miles"
    )
    timezone_offset_minutes = serializers.IntegerField(
        required=False,
        default=None,
        allow_null=True,
        help_text="Client timezone offset from UTC in minutes (from Date.getTimezoneOffset())"
    )
    allow_simulated_fallback = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Allow explicitly labeled simulated routes if external road routing is down"
    )

    def validate_departure_time(self, value):
        clean = value.strip().replace("Z", "+00:00")
        try:
            datetime.fromisoformat(clean)
            return value
        except Exception:
            raise serializers.ValidationError(
                "Invalid departure date/time format. Use ISO 8601 (e.g., YYYY-MM-DDTHH:MM or YYYY-MM-DDTHH:MM:SSZ)."
            )

    def validate(self, data):
        if data["origin"].lower() == data["destination"].lower():
            raise serializers.ValidationError("Origin and destination must be different locations.")
        return data
