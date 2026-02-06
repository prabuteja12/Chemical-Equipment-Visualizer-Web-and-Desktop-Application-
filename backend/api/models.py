from django.db import models


class Dataset(models.Model):
    name = models.CharField(max_length=255)
    csv_file = models.FileField(upload_to="datasets/")
    created_at = models.DateTimeField(auto_now_add=True)
    row_count = models.IntegerField(default=0)
    avg_flowrate = models.FloatField(default=0.0)
    avg_pressure = models.FloatField(default=0.0)
    avg_temperature = models.FloatField(default=0.0)
    type_distribution = models.JSONField(default=dict)
    summary = models.JSONField(default=dict)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.created_at:%Y-%m-%d %H:%M})"
