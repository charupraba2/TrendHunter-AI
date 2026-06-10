"""PDF report generation for creator analysis results."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class ReportService:
    def build_pdf(self, payload: dict[str, Any]) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "TrendHunterTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0f172a"),
            alignment=TA_LEFT,
            spaceAfter=10,
        )
        heading_style = ParagraphStyle(
            "TrendHunterHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#10b981"),
            spaceBefore=10,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "TrendHunterBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=3,
        )
        small_style = ParagraphStyle(
            "TrendHunterSmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#4b5563"),
        )

        analysis = payload.get("analysis") or payload
        current_request = payload.get("current_request") or {}
        recommendations = payload.get("recommendations") or analysis.get("recommendations") or {}
        forecast = payload.get("forecast") or analysis.get("forecast") or {}
        linkedin_post = (
            payload.get("linkedin_post")
            or payload.get("linkedin_post_text")
            or analysis.get("linkedin_post")
            or analysis.get("linkedin_post_text")
            or ""
        )
        thumbnail_result = (
            payload.get("thumbnail_result")
            or payload.get("thumbnail_analysis")
            or analysis.get("thumbnail_result")
            or analysis.get("thumbnail_analysis")
            or {}
        )
        competitor_analysis = payload.get("competitor_analysis") or payload.get("competitor_result") or {}
        timestamp = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
        hashtags = self._normalize_hashtags(
            payload.get("hashtags")
            or current_request.get("hashtags")
            or analysis.get("normalized_hashtags")
            or []
        )

        story = [
            Paragraph("TrendHunter AI Creator Intelligence Report", title_style),
            Paragraph(f"Generated at: {self._escape(timestamp)}", small_style),
            Spacer(1, 0.15 * inch),
            Paragraph("Summary", heading_style),
            Paragraph(self._escape(self._summary_text(payload)), body_style),
            Spacer(1, 0.08 * inch),
        ]

        metrics_data = [
            ["Title", self._escape(current_request.get("title") or payload.get("title") or "N/A")],
            ["Caption", self._escape(current_request.get("caption") or payload.get("caption") or "N/A")],
            ["Platform", self._escape(current_request.get("platform_label") or current_request.get("platform") or payload.get("platform") or "N/A")],
            ["Audience", self._escape(current_request.get("audience") or payload.get("audience") or "N/A")],
            ["Virality Score", self._escape(analysis.get("virality_score") or payload.get("virality_score") or 0)],
            ["Trend Match Score", self._escape(payload.get("trend_match_score") or analysis.get("trend_match_score") or 0)],
            ["Prediction", self._escape(analysis.get("prediction_label") or payload.get("prediction_label") or "Pending")],
        ]

        table = Table(metrics_data, colWidths=[1.7 * inch, 4.7 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcfce7")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("LEADING", (0, 0), (-1, -1), 11),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.whitesmoke, colors.HexColor("#f8fafc")]),
                ]
            )
        )

        sections = [
            Paragraph("Metric Breakdown", heading_style),
            table,
            Spacer(1, 0.1 * inch),
            Paragraph("Recommendations", heading_style),
            Paragraph(self._escape(self._join_list(recommendations.get("recommended_actions") or analysis.get("recommended_creator_actions") or [])), body_style),
            Paragraph(self._escape(self._join_list(forecast.get("recommended_creator_actions") or [])), body_style),
            Paragraph("Forecast", heading_style),
            Paragraph(self._escape(forecast.get("forecast_explanation") or forecast.get("why_the_trend_may_grow") or "No forecast available."), body_style),
            Paragraph("LinkedIn Post", heading_style),
            Paragraph(self._escape(linkedin_post or "No LinkedIn post has been generated yet."), body_style),
            Paragraph("Thumbnail Analysis", heading_style),
            Paragraph(self._escape(self._thumbnail_summary(thumbnail_result)), body_style),
            Paragraph("Competitor Analysis", heading_style),
            Paragraph(self._escape(self._competitor_summary(competitor_analysis)), body_style),
            Paragraph("Hashtags", heading_style),
            Paragraph(self._escape(" ".join(hashtags) or "No hashtags available."), body_style),
        ]

        doc.build([*story, *sections])
        buffer.seek(0)
        return buffer.read()

    def _summary_text(self, payload: dict[str, Any]) -> str:
        analysis = payload.get("analysis") or payload
        title = payload.get("current_request", {}).get("title") or payload.get("title") or "this idea"
        virality = analysis.get("virality_score") or payload.get("virality_score") or 0
        summary = analysis.get("summary") or payload.get("summary") or "This report captures the latest creator intelligence result."
        return f"{title} scored {virality} on virality. {summary}"

    def _join_list(self, values: Any) -> str:
        if not isinstance(values, list):
            return str(values or "")
        return " ".join(str(item) for item in values if item)

    def _normalize_hashtags(self, hashtags: Any) -> list[str]:
        if hashtags is None:
            return []
        if isinstance(hashtags, list):
            values = hashtags
        else:
            values = str(hashtags).replace(",", " ").split()
        normalized: list[str] = []
        for item in values:
            token = str(item).strip()
            if not token:
                continue
            if not token.startswith("#"):
                token = f"#{token.lstrip('#')}"
            normalized.append(token)
        return list(dict.fromkeys(normalized))

    def _escape(self, value: Any) -> str:
        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def _thumbnail_summary(self, thumbnail_result: Any) -> str:
        if not isinstance(thumbnail_result, dict) or not thumbnail_result:
            return "No thumbnail analysis has been uploaded yet."

        parts = [
            f"Score: {thumbnail_result.get('thumbnail_score', 'N/A')}",
            f"Brightness: {thumbnail_result.get('brightness', 'N/A')}",
            f"Contrast: {thumbnail_result.get('contrast', 'N/A')}",
            f"Resolution: {thumbnail_result.get('width', 'N/A')} x {thumbnail_result.get('height', 'N/A')}",
        ]
        issues = thumbnail_result.get("issues") or []
        suggestions = thumbnail_result.get("suggestions") or []
        if issues:
            parts.append("Issues: " + "; ".join(str(item) for item in issues))
        if suggestions:
            parts.append("Suggestions: " + "; ".join(str(item) for item in suggestions))
        return " | ".join(parts)

    def _competitor_summary(self, competitor_analysis: Any) -> str:
        if not isinstance(competitor_analysis, dict) or not competitor_analysis:
            return "No competitor analysis has been generated yet."
        parts = [
            f"Competitor: {competitor_analysis.get('competitor', 'N/A')}",
            f"Platform: {competitor_analysis.get('platform_label') or competitor_analysis.get('platform', 'N/A')}",
            f"Style: {competitor_analysis.get('content_style', 'N/A')}",
            f"Pattern: {competitor_analysis.get('posting_pattern', 'N/A')}",
        ]
        hooks = competitor_analysis.get("common_hook_words") or []
        recommendations = competitor_analysis.get("strategy_recommendations") or []
        if hooks:
            parts.append("Hooks: " + ", ".join(f"{item.get('word')} ({item.get('count')})" for item in hooks[:5] if isinstance(item, dict)))
        if recommendations:
            parts.append("Recommendations: " + "; ".join(str(item) for item in recommendations[:5]))
        return " | ".join(parts)


report_service = ReportService()
