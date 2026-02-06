from rest_framework import serializers
from .models import Dataset


class DatasetListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = [
            "id",
            "name",
            "created_at",
            "row_count",
            "avg_flowrate",
            "avg_pressure",
            "avg_temperature",
            "type_distribution",
        ]


class DatasetDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = [
            "id",
            "name",
            "created_at",
            "row_count",
            "avg_flowrate",
            "avg_pressure",
            "avg_temperature",
            "type_distribution",
            "summary",
        ]
