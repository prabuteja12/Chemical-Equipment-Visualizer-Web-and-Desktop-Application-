from django.urls import path
from . import views


urlpatterns = [
    path("upload/", views.UploadDatasetView.as_view()),
    path("datasets/", views.DatasetListView.as_view()),
    path("datasets/<int:pk>/", views.DatasetDetailView.as_view()),
    path("datasets/<int:pk>/report/", views.DatasetReportView.as_view()),
    path("datasets/<int:pk>/email/", views.DatasetEmailView.as_view()),
    path("datasets/<int:pk>/live/", views.DatasetLiveView.as_view()),
]
