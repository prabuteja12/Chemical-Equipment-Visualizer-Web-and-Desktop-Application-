import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from django.conf import settings
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.utils.timezone import localtime

from rest_framework import generics
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Dataset
from .serializers import DatasetListSerializer, DatasetDetailSerializer
from .utils import analyze_csv, preview_rows, generate_live_signals, _normalize_dataframe, _coerce_numeric


def _prune_old_datasets(keep: int = 5):
    datasets = Dataset.objects.all().order_by("-created_at")
    if datasets.count() <= keep:
        return
    for dataset in datasets[keep:]:
        dataset.csv_file.delete(save=False)
        dataset.delete()


def _logo_image() -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(1.2, 1.2), dpi=100)
    ax.axis("off")
    circle = plt.Circle((0.5, 0.5), 0.45, color="#FF7A00")
    ax.add_artist(circle)
    ax.text(0.5, 0.5, "CEV", color="white", fontsize=16, fontweight="bold", ha="center", va="center")
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=120, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    buffer.seek(0)
    return buffer


def _dashboard_chart_image(df: pd.DataFrame, type_distribution: dict) -> io.BytesIO:
    fig, axs = plt.subplots(2, 2, figsize=(8, 6))
    fig.patch.set_facecolor("white")

    labels = list(type_distribution.keys())
    values = list(type_distribution.values())
    axs[0, 0].bar(labels, values, color="#FF7A00")
    axs[0, 0].set_title("Equipment Mix", fontsize=10)
    axs[0, 0].tick_params(axis="x", rotation=20, labelsize=8)
    axs[0, 0].grid(axis="y", alpha=0.2)

    scatter_df = df.dropna(subset=["Pressure", "Flowrate"])
    axs[0, 1].scatter(scatter_df["Pressure"], scatter_df["Flowrate"], color="#2EC4B6", alpha=0.7, s=12)
    axs[0, 1].set_title("Pressure vs Flowrate", fontsize=10)
    axs[0, 1].tick_params(labelsize=8)
    axs[0, 1].grid(alpha=0.2)

    temp_rows = df.head(20)
    axs[1, 0].plot(temp_rows["Equipment Name"], temp_rows["Temperature"], color="#4C6FFF")
    axs[1, 0].set_title("Temperature Profile", fontsize=10)
    axs[1, 0].tick_params(axis="x", rotation=35, labelsize=7)
    axs[1, 0].grid(axis="y", alpha=0.2)

    flow = df["Flowrate"].dropna().tolist()
    if flow:
        min_v = min(flow)
        max_v = max(flow)
        span = max_v - min_v or 1
        bin_count = 6
        bin_size = span / bin_count
        bins = [0] * bin_count
        for val in flow:
            idx = min(bin_count - 1, int((val - min_v) / bin_size))
            bins[idx] += 1
        labels_hist = []
        for i in range(bin_count):
            start = min_v + i * bin_size
            end = start + bin_size
            labels_hist.append(f"{start:.1f}-{end:.1f}")
        axs[1, 1].bar(labels_hist, bins, color="#4C6FFF", alpha=0.8)
        axs[1, 1].set_title("Flowrate Distribution", fontsize=10)
        axs[1, 1].tick_params(axis="x", rotation=20, labelsize=7)
        axs[1, 1].grid(axis="y", alpha=0.2)
    else:
        axs[1, 1].text(0.5, 0.5, "No flowrate data", ha="center", va="center", fontsize=8)

    fig.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=180)
    plt.close(fig)
    buffer.seek(0)
    return buffer


def _build_pdf_report(dataset: Dataset) -> bytes:
    summary = dataset.summary or {}
    type_distribution = summary.get("type_distribution", dataset.type_distribution)
    created_at = localtime(dataset.created_at)

    with dataset.csv_file.open("rb") as handle:
        df = pd.read_csv(handle)
    df = _normalize_dataframe(df)
    df = _coerce_numeric(df)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    left = 40
    right = width - 40
    bottom = 40
    line_height = 14
    y = height - 80

    def draw_header():
        pdf.setFillColor(colors.HexColor("#FF7A00"))
        pdf.rect(0, height - 70, width, 70, fill=1, stroke=0)
        logo = _logo_image()
        pdf.drawImage(ImageReader(logo), 16, height - 62, width=36, height=36, mask="auto")
        pdf.setFillColor(colors.white)
        pdf.setFont("Times-Bold", 16)
        pdf.drawString(60, height - 45, "Chemical Equipment Visualizer")
        pdf.setFont("Times-Roman", 10)
        pdf.drawString(60, height - 60, "Process Intelligence Report")
        pdf.setFillColor(colors.black)

    def draw_page_number():
        pdf.setFont("Times-Roman", 8)
        pdf.setFillColor(colors.HexColor("#94a3b8"))
        pdf.drawRightString(width - 40, 20, f"Page {pdf.getPageNumber()}")
        pdf.setFillColor(colors.black)

    draw_header()

    pdf.setFont("Times-Bold", 12)
    pdf.drawString(left, y, f"Dataset: {dataset.name}")
    y -= line_height
    pdf.setFont("Times-Roman", 10)
    pdf.drawString(left, y, f"Uploaded: {created_at.strftime('%Y-%m-%d %H:%M')}")
    y -= line_height * 1.2

    pdf.setFont("Times-Bold", 11)
    pdf.drawString(left, y, "Summary")
    y -= line_height
    pdf.setFont("Times-Roman", 10)
    pdf.drawString(left, y, f"Total Records: {summary.get('row_count', dataset.row_count)}")
    y -= line_height
    pdf.drawString(left, y, f"Average Flowrate: {summary.get('avg_flowrate', dataset.avg_flowrate):.2f}")
    y -= line_height
    pdf.drawString(left, y, f"Average Pressure: {summary.get('avg_pressure', dataset.avg_pressure):.2f}")
    y -= line_height
    pdf.drawString(left, y, f"Average Temperature: {summary.get('avg_temperature', dataset.avg_temperature):.2f}")
    y -= line_height * 1.4

    pdf.setFont("Times-Bold", 11)
    pdf.drawString(left, y, "Equipment Records (Full)")
    y -= line_height

    headers = ["Equipment Name", "Type", "Flowrate", "Pressure", "Temperature"]
    col_x = [left, left + 180, left + 300, left + 380, left + 460]
    pdf.setFont("Times-Bold", 10)
    for idx, header in enumerate(headers):
        pdf.drawString(col_x[idx], y, header)
    y -= line_height
    pdf.setLineWidth(0.5)
    pdf.line(left, y + 6, right, y + 6)
    pdf.setFont("Times-Roman", 10)

    for idx, row in df.iterrows():
        if y < bottom + 60:
            break
        if idx % 2 == 0:
            pdf.setFillColor(colors.HexColor("#f1f5f9"))
            pdf.rect(left, y - 2, right - left, line_height, fill=1, stroke=0)
            pdf.setFillColor(colors.black)
        pdf.drawString(col_x[0], y, str(row.get("Equipment Name", ""))[:22])
        pdf.drawString(col_x[1], y, str(row.get("Type", ""))[:12])
        pdf.drawString(col_x[2], y, str(row.get("Flowrate", ""))[:8])
        pdf.drawString(col_x[3], y, str(row.get("Pressure", ""))[:8])
        pdf.drawString(col_x[4], y, str(row.get("Temperature", ""))[:8])
        y -= line_height

    draw_page_number()
    pdf.showPage()

    # Page 2: Visualizations
    pdf.setFont("Times-Bold", 12)
    pdf.drawString(left, height - 40, "Visualizations")
    chart = _dashboard_chart_image(df, type_distribution or {})
    pdf.drawImage(ImageReader(chart), left, 120, width=right - left, height=height - 200, preserveAspectRatio=True)
    draw_page_number()
    pdf.save()
    buffer.seek(0)
    return buffer.read()


class UploadDatasetView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if "file" not in request.data:
            return Response({"detail": "CSV file required."}, status=400)
        file_obj = request.data["file"]
        df, summary = analyze_csv(file_obj)
        rows = preview_rows(df, limit=500)
        summary["rows_preview"] = rows

        dataset = Dataset.objects.create(
            name=file_obj.name,
            csv_file=file_obj,
            row_count=summary["row_count"],
            avg_flowrate=summary["avg_flowrate"],
            avg_pressure=summary["avg_pressure"],
            avg_temperature=summary["avg_temperature"],
            type_distribution=summary["type_distribution"],
            summary=summary,
        )
        _prune_old_datasets(keep=5)
        serializer = DatasetDetailSerializer(dataset)
        data = serializer.data
        data["rows"] = rows
        data["columns"] = summary.get("columns", [])
        return Response(data)


class DatasetListView(generics.ListAPIView):
    queryset = Dataset.objects.all().order_by("-created_at")
    serializer_class = DatasetListSerializer


class DatasetDetailView(APIView):
    def get(self, request, pk):
        include_rows = request.query_params.get("include_rows") == "1"
        dataset = Dataset.objects.get(pk=pk)
        serializer = DatasetDetailSerializer(dataset)
        data = serializer.data
        if include_rows:
            try:
                with dataset.csv_file.open("rb") as handle:
                    df = pd.read_csv(handle)
                df = _normalize_dataframe(df)
                df = _coerce_numeric(df)
                data["rows"] = preview_rows(df, limit=500)
                data["columns"] = data.get("summary", {}).get("columns", [])
            except Exception:
                data["rows"] = []
                data["columns"] = data.get("summary", {}).get("columns", [])
        return Response(data)


class DatasetReportView(APIView):
    def get(self, request, pk):
        dataset = Dataset.objects.get(pk=pk)
        pdf_bytes = _build_pdf_report(dataset)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="report_{pk}.pdf"'
        return response


class DatasetEmailView(APIView):
    def post(self, request, pk):
        email = request.data.get("email")
        if not email:
            return Response({"detail": "Email required."}, status=400)
        dataset = Dataset.objects.get(pk=pk)
        pdf_bytes = _build_pdf_report(dataset)
        message = EmailMessage(
            subject=f"Chemical Equipment Report - {dataset.name}",
            body="Please find attached the PDF report.",
            from_email=settings.EMAIL_HOST_USER,
            to=[email],
        )
        message.attach(f"report_{pk}.pdf", pdf_bytes, "application/pdf")
        message.send(fail_silently=False)
        return Response({"detail": "Email sent."})


class DatasetLiveView(APIView):
    def get(self, request, pk):
        dataset = Dataset.objects.get(pk=pk)
        summary = dataset.summary or {}
        stats = summary.get("stats", {})
        points = int(request.query_params.get("points", 24))
        live = generate_live_signals(stats, points=points)
        return Response({"live": live})
