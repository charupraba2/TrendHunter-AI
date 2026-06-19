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
from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class ReportService:
    def build_industry_pdf(self, payload: dict[str, Any]) -> bytes:
        return self._build_dynamic_industry_pdf(payload or {})

    def _build_dynamic_industry_pdf(self, payload: dict[str, Any]) -> bytes:
        return self._render_industry_pdf_report(payload)

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=34,
            leftMargin=34,
            topMargin=34,
            bottomMargin=34,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "IndustryTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=23,
            textColor=colors.HexColor("#0f172a"),
            alignment=TA_LEFT,
            spaceAfter=8,
        )
        subtitle_style = ParagraphStyle(
            "IndustrySubtitle",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#475569"),
            spaceAfter=2,
        )
        heading_style = ParagraphStyle(
            "IndustryHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#10b981"),
            spaceBefore=10,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "IndustryBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=4,
        )
        small_style = ParagraphStyle(
            "IndustrySmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#64748b"),
        )

        def paragraph(value: Any, style=body_style) -> Paragraph:
            return Paragraph(self._escape(value or "N/A"), style)

        def rich_paragraph(html: str, style=body_style) -> Paragraph:
            return Paragraph(html or "N/A", style)

        def safe_text(value: Any, default: str = "N/A") -> str:
            text = str(value or "").strip()
            return text if text else default

        def safe_number(value: Any, default: int = 0, cap: int | None = None) -> int:
            try:
                number = int(round(float(value)))
            except (TypeError, ValueError):
                number = default
            if cap is not None:
                number = min(number, cap)
            return number

        def normalize_direction(value: Any) -> str:
            text = str(value or "").strip().lower()
            if text in {"rising", "rise", "up", "very high", "high"}:
                return "Rising"
            if text in {"falling", "down", "declining", "weak", "low"}:
                return "Falling"
            return "Stable"

        def trend_board_score(trend: dict[str, Any]) -> int:
            base = safe_number(trend.get("trend_score") or trend.get("momentum_score"), 50, 100)
            growth = safe_number(trend.get("growth_score"), 50, 100)
            source_bonus = min(8, safe_number(trend.get("source_count"), 0, 20))
            recency_bonus = 0
            direction = normalize_direction(trend.get("direction") or trend.get("signal_strength"))
            if direction == "Rising":
                recency_bonus = 4
            elif direction == "Stable":
                recency_bonus = 1
            board_score = round(base * 0.6 + growth * 0.3 + source_bonus + recency_bonus)
            if trend.get("trend_name") in {"ChatGPT", "Claude", "Gemini", "OpenAI", "Anthropic", "Agentic AI", "MCP"}:
                board_score += 6
            elif trend.get("trend_name") in {"AI Governance", "AI Security", "LLM Security", "AI Compliance", "AI Risk", "Model Monitoring", "Trustworthy AI"}:
                board_score += 4
            return min(95, max(0, board_score))

        def momentum_label(score: int) -> str:
            if score >= 85:
                return "Very High"
            if score >= 70:
                return "High"
            if score >= 50:
                return "Moderate"
            return "Low"

        def recommendation_category(item: dict[str, Any]) -> str:
            text = " ".join(
                str(item.get(key) or "")
                for key in ("trend", "reason", "why_it_matters", "recommended_action", "business_impact")
            ).lower()
            if any(token in text for token in ["revenue", "pricing", "pipeline", "sell", "upsell", "mrr", "gtm"]):
                return "Revenue"
            if any(token in text for token in ["risk", "compliance", "security", "privacy", "audit", "governance"]):
                return "Risk"
            if any(token in text for token in ["product", "feature", "platform", "workflow", "integration", "roadmap"]):
                return "Product"
            if any(token in text for token in ["competitive", "competitor", "position", "positioning", "differentiat"]):
                return "Competitive"
            return "Strategic"

        def category_priority(category: str) -> int:
            return {"Strategic": 0, "Product": 1, "Revenue": 2, "Risk": 3, "Competitive": 4}.get(category, 5)

        def to_bullets(items: list[str]) -> str:
            cleaned = [item for item in (safe_text(value, "").strip() for value in items) if item]
            if not cleaned:
                return "N/A"
            return "<br/>".join(f"- {self._escape(item)}" for item in cleaned)

        def build_horizontal_chart(labels: list[str], values: list[int], title: str, value_label: str) -> Drawing:
            width = 500
            height = max(120, 24 * max(3, len(labels)) + 20)
            drawing = Drawing(width, height)
            drawing.add(String(0, height - 12, title, fontName="Helvetica-Bold", fontSize=9.5, fillColor=colors.HexColor("#334155")))
            chart = HorizontalBarChart()
            chart.x = 120
            chart.y = 18
            chart.height = height - 42
            chart.width = width - 150
            chart.data = [values or [0]]
            chart.barWidth = 10
            chart.groupSpacing = 8
            chart.categoryAxis.categoryNames = labels or ["N/A"]
            chart.categoryAxis.labels.boxAnchor = "e"
            chart.categoryAxis.labels.fontName = "Helvetica"
            chart.categoryAxis.labels.fontSize = 8
            chart.categoryAxis.labels.fillColor = colors.HexColor("#334155")
            chart.categoryAxis.visibleGrid = False
            chart.valueAxis.valueMin = 0
            chart.valueAxis.valueMax = 100
            chart.valueAxis.valueStep = 20
            chart.valueAxis.labels.fontName = "Helvetica"
            chart.valueAxis.labels.fontSize = 8
            chart.bars[0].fillColor = colors.HexColor("#10b981")
            drawing.add(chart)
            drawing.add(String(390, 6, value_label, fontName="Helvetica", fontSize=7.5, fillColor=colors.HexColor("#64748b")))
            return drawing

        def build_vertical_chart(labels: list[str], values: list[int], title: str, accent: str = "#10b981") -> Drawing:
            width = 500
            height = 200
            drawing = Drawing(width, height)
            drawing.add(String(0, height - 12, title, fontName="Helvetica-Bold", fontSize=9.5, fillColor=colors.HexColor("#334155")))
            chart = VerticalBarChart()
            chart.x = 25
            chart.y = 25
            chart.height = 118
            chart.width = width - 55
            chart.data = [values or [0]]
            chart.barWidth = 16
            chart.groupSpacing = 12
            chart.categoryAxis.categoryNames = labels or ["N/A"]
            chart.categoryAxis.labels.angle = 35
            chart.categoryAxis.labels.dx = 6
            chart.categoryAxis.labels.dy = -10
            chart.categoryAxis.labels.fontName = "Helvetica"
            chart.categoryAxis.labels.fontSize = 7
            chart.categoryAxis.labels.fillColor = colors.HexColor("#334155")
            chart.valueAxis.valueMin = 0
            chart.valueAxis.valueMax = 100
            chart.valueAxis.valueStep = 20
            chart.valueAxis.labels.fontName = "Helvetica"
            chart.valueAxis.labels.fontSize = 8
            chart.bars[0].fillColor = colors.HexColor(accent)
            drawing.add(chart)
            return drawing

        def section_table(headers: list[str], rows: list[list[Any]], col_widths: list[float]) -> Table:
            data = [[Paragraph(f"<b>{self._escape(h)}</b>", body_style) for h in headers]]
            for row in rows:
                data.append([paragraph(cell) for cell in row])
            table = Table(data, colWidths=col_widths, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcfce7")),
                        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                        ("LEADING", (0, 0), (-1, -1), 11),
                        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#d1d5db")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#f8fafc")]),
                    ]
                )
            )
            return table

        generated_at = payload.get("generated_at") or datetime.now(timezone.utc).isoformat()
        company = payload.get("company") or {}
        trends = payload.get("top_trends") or []
        search_highlights = payload.get("search_highlights") or []
        competitors = payload.get("competitors") or []
        opportunities = payload.get("opportunities") or []
        recommendations = payload.get("recommendations") or []
        source_coverage = payload.get("source_coverage") or {}
        executive = payload.get("executive_summary") or {}

        trend_items = sorted(
            [trend for trend in trends if isinstance(trend, dict)],
            key=lambda trend: (trend_board_score(trend), safe_number(trend.get("growth_score"), 0, 100)),
            reverse=True,
        )
        trend_labels = [safe_text(trend.get("trend_name"), "Trend") for trend in trend_items[:6]]
        trend_values = [trend_board_score(trend) for trend in trend_items[:6]]

        competitor_items = sorted(
            [item for item in competitors if isinstance(item, dict)],
            key=lambda item: safe_number(item.get("momentum_score") or item.get("market_momentum_score"), 0, 100),
            reverse=True,
        )
        competitor_labels = [safe_text(item.get("name") or item.get("competitor_name"), "Competitor") for item in competitor_items[:6]]
        competitor_values = [safe_number(item.get("momentum_score") or item.get("market_momentum_score"), 0, 100) for item in competitor_items[:6]]

        opportunity_items = sorted(
            [item for item in opportunities if isinstance(item, dict)],
            key=lambda item: safe_number(item.get("priority_score") or item.get("urgency_score") or item.get("impact_score"), 0, 100),
            reverse=True,
        )
        opportunity_labels = [safe_text(item.get("opportunity_name") or item.get("title"), "Opportunity") for item in opportunity_items[:6]]
        opportunity_values = [
            safe_number(item.get("priority_score") or item.get("urgency_score") or item.get("impact_score"), 50, 100)
            for item in opportunity_items[:6]
        ]

        grouped_recommendations: dict[str, list[dict[str, Any]]] = {
            "Strategic": [],
            "Product": [],
            "Revenue": [],
            "Risk": [],
            "Competitive": [],
        }
        for item in recommendations:
            if isinstance(item, dict):
                grouped_recommendations.setdefault(recommendation_category(item), []).append(item)
        for group in grouped_recommendations.values():
            group.sort(
                key=lambda item: safe_number(item.get("priority_score") or item.get("confidence_score"), 0, 100),
                reverse=True,
            )
        for category, group in grouped_recommendations.items():
            deduped: list[dict[str, Any]] = []
            seen_signatures: set[str] = set()
            for item in group:
                signature = " ".join(
                    str(item.get(key) or "").strip().lower()
                    for key in ("trend", "insight_title", "recommendation", "title", "reason", "why_it_matters")
                ).strip()
                if signature in seen_signatures:
                    continue
                seen_signatures.add(signature)
                deduped.append(item)
            grouped_recommendations[category] = deduped

        key_takeaways = [
            safe_text(
                executive.get("top_signal")
                or (
                    f"{trend_items[0].get('trend_name')} is the clearest market signal today and it is shaping enterprise purchase decisions."
                    if trend_items
                    else "Enterprise AI is setting the board agenda."
                )
            ),
            safe_text(
                executive.get("main_opportunity")
                or (
                    f"{opportunity_items[0].get('opportunity_name')} is the most immediate commercial opening for Giggso."
                    if opportunity_items
                    else "There is a clear opportunity to package governance as a growth lever."
                )
            ),
            safe_text(
                executive.get("main_risk")
                or "Adoption is outpacing governance controls, raising execution and compliance risk."
            ),
        ]
        top_risks = [
            safe_text(
                executive.get("main_risk")
                or "AI adoption is moving faster than governance, auditability, and monitoring controls."
            ),
            safe_text(next((item.get("reason") or item.get("why_it_matters") for item in grouped_recommendations.get("Risk", [])[:1]), ""), ""),
            safe_text(next((item.get("reason") or item.get("why_it_matters") for item in grouped_recommendations.get("Competitive", [])[:1]), ""), ""),
        ]
        ninety_day_opps = [
            safe_text(
                opportunity_items[0].get("opportunity_name")
                if opportunity_items
                else "Launch a board-ready governance assessment package."
            ),
            safe_text(
                opportunity_items[1].get("opportunity_name")
                if len(opportunity_items) > 1
                else "Turn model monitoring into an executive visibility story."
            ),
            safe_text(
                opportunity_items[2].get("opportunity_name")
                if len(opportunity_items) > 2
                else "Package enterprise AI controls into a differentiated revenue motion."
            ),
        ]

        narrative_paragraphs = [
            (
                "Enterprise AI is moving from experimentation to operationalized deployment, and that shift is making governance, "
                "security, and monitoring core buying criteria rather than optional add-ons. In this market, vendors are judged on "
                "whether they can reduce risk while helping teams ship AI into production."
            ),
            (
                "For Giggso, the strategic opening is clear: position AI governance as an accelerator of enterprise adoption. "
                "The strongest categories in this report are not isolated technologies, but the control layers that make models, "
                "agents, and retrieval systems safe enough for regulated environments."
            ),
            (
                "The board implication is that product, risk, and revenue motions should be aligned. The companies that win the next "
                "phase of enterprise AI will be the ones that can show measurable control, credible proof, and a direct path from "
                "trust to commercial value."
            ),
        ]

        story: list[Any] = [
            Paragraph("Enterprise AI Market Intelligence Report", title_style),
            Paragraph(f"Reference Company: {self._escape(company.get('company_name') or 'Giggso')}", subtitle_style),
            Paragraph(f"Generated: {self._escape(generated_at)}", subtitle_style),
            Spacer(1, 0.15 * inch),
            Paragraph("Executive Summary", heading_style),
            paragraph(narrative_paragraphs[0]),
            paragraph(narrative_paragraphs[1]),
            paragraph(narrative_paragraphs[2]),
            paragraph(
                " | ".join(
                    [
                        f"Top market signal: {executive.get('top_signal') or 'N/A'}",
                        f"Main opportunity: {executive.get('main_opportunity') or 'N/A'}",
                        f"Main risk: {executive.get('main_risk') or 'N/A'}",
                        f"Recommended action: {executive.get('recommended_action') or 'N/A'}",
                    ]
                )
            ),
            Paragraph("Key Takeaways", heading_style),
            rich_paragraph(to_bullets(key_takeaways)),
            Paragraph("Top Risks", heading_style),
            rich_paragraph(to_bullets(top_risks)),
            Paragraph("Next 90-Day Opportunities", heading_style),
            rich_paragraph(to_bullets(ninety_day_opps)),
            Paragraph("Top Industry Trends", heading_style),
        ]

        trend_rows = [
            [
                safe_text(trend.get("trend_name"), "Trend"),
                f"{trend_board_score(trend)}",
                f"{safe_number(trend.get('growth_score'), 0, 100)}",
                normalize_direction(trend.get("direction") or trend.get("signal_strength")),
                trend.get("executive_summary") or trend.get("summary") or "",
            ]
            for trend in trend_items[:8]
        ]
        story.extend(
            [
                build_horizontal_chart(trend_labels, trend_values, "Trend Ranking Chart", "Board score blends trend, growth, source count, and recency."),
                Spacer(1, 0.08 * inch),
                section_table(
                    ["Trend", "Board Score", "Growth", "Direction", "Executive Summary"],
                    trend_rows or [["No trends available", "-", "-", "-", "No live trend data available."]],
                    [1.25 * inch, 0.7 * inch, 0.7 * inch, 0.9 * inch, 3.15 * inch],
                ),
                Spacer(1, 0.09 * inch),
                Paragraph("Search Intelligence Highlights", heading_style),
            ]
        )

        search_rows = [
            [
                item.get("query"),
                f"{int(round(float(item.get('trend_score') or 0)))}",
                item.get("momentum") or "Stable",
                ", ".join(item.get("related_keywords") or [])[:140],
                item.get("executive_summary") or "",
            ]
            for item in search_highlights[:6]
        ]
        story.extend(
            [
                section_table(
                    ["Query", "Score", "Momentum", "Related Keywords", "Executive Summary"],
                    search_rows or [["No highlights available", "-", "-", "-", "No search intelligence available."]],
                    [1.0 * inch, 0.65 * inch, 0.85 * inch, 1.9 * inch, 2.2 * inch],
                ),
                Spacer(1, 0.09 * inch),
                Paragraph("Competitor Intelligence", heading_style),
                build_vertical_chart(competitor_labels, competitor_values, "Competitor Momentum Chart", "#0f766e"),
            ]
        )

        competitor_rows = [
            [
                safe_text(item.get("name") or item.get("competitor_name"), "Competitor"),
                item.get("focus_area") or "",
                item.get("activity_summary") or "",
                f"{safe_number(item.get('momentum_score') or item.get('market_momentum_score'), 0, 100)}",
            ]
            for item in competitor_items[:6]
        ]
        story.extend(
            [
                section_table(
                    ["Competitor", "Focus Area", "Activity Summary", "Momentum"],
                    competitor_rows or [["No competitors available", "-", "-", "-"]],
                    [1.05 * inch, 1.55 * inch, 2.85 * inch, 0.75 * inch],
                ),
                Spacer(1, 0.09 * inch),
                Paragraph("Giggso Positioning", heading_style),
                paragraph(
                    " | ".join(
                        [
                            f"Company focus areas: {', '.join(company.get('core_focus_areas') or []) or 'N/A'}",
                            f"Strategic themes: {', '.join(company.get('recent_strategic_themes') or company.get('strategic_themes') or []) or 'N/A'}",
                            f"Market positioning: {company.get('market_positioning') or company.get('industry_positioning') or 'N/A'}",
                        ]
                    )
                ),
                Paragraph("Market Opportunities", heading_style),
                build_vertical_chart(opportunity_labels, opportunity_values, "Opportunity Priority Chart", "#2563eb"),
            ]
        )

        opportunity_rows = [
            [
                safe_text(item.get("opportunity_name") or item.get("title"), "Opportunity"),
                item.get("business_value") or item.get("summary") or "",
                item.get("target_buyer") or "",
                item.get("urgency") or "",
            ]
            for item in opportunity_items[:6]
        ]
        story.extend(
            [
                section_table(
                    ["Opportunity", "Business Impact", "Recommended Action / Buyer", "Priority"],
                    opportunity_rows or [["No opportunities available", "-", "-", "-"]],
                    [1.3 * inch, 2.5 * inch, 1.8 * inch, 0.75 * inch],
                ),
                Spacer(1, 0.09 * inch),
                Paragraph("Executive Recommendations", heading_style),
            ]
        )

        for category in ["Strategic", "Product", "Revenue", "Risk", "Competitive"]:
            items = grouped_recommendations.get(category) or []
            story.append(Paragraph(f"{category} Recommendations", heading_style))
            category_rows = [
                [
                    safe_text(item.get("trend") or item.get("insight_title") or item.get("recommendation") or item.get("title"), "Recommendation"),
                    " ".join(
                        part
                        for part in [
                            safe_text(item.get("reason") or item.get("why_it_matters") or "", ""),
                            safe_text(item.get("recommended_action") or item.get("business_impact") or "", ""),
                        ]
                        if part
                    ),
                    safe_text(item.get("priority") or item.get("confidence_score") or "", "Medium"),
                ]
                for item in items[:3]
            ]
            story.extend(
                [
                    section_table(
                        ["Recommendation", "Reason", "Priority"],
                        category_rows or [["No recommendations available", "-", "-"]],
                        [2.1 * inch, 3.35 * inch, 0.95 * inch],
                    ),
                    Spacer(1, 0.09 * inch),
                ]
            )
        story.extend(
            [
                Paragraph("Executive Readout", heading_style),
                paragraph(
                    "The most actionable motion is to connect governance, observability, and security controls to measurable enterprise outcomes. "
                    "That creates a cleaner story for regulated buyers and a stronger wedge against safety-first and platform-first competitors."
                ),
                Paragraph("Top Risks", heading_style),
                paragraph(to_bullets(top_risks)),
                Paragraph("Next 90-Day Opportunities", heading_style),
                paragraph(to_bullets(ninety_day_opps)),
                Paragraph("Source Coverage", heading_style),
                paragraph(
                    " | ".join(
                        [
                            f"Giggso Website: {source_coverage.get('company') or 'Available'}",
                            f"LinkedIn: {source_coverage.get('linkedin') or 'Available'}",
                            f"News: {source_coverage.get('news') or 'Available'}",
                            f"Competitors: {source_coverage.get('competitors') or 'Available'}",
                            f"AI Insights: {source_coverage.get('insights') or 'Fallback'}",
                            f"Last Refreshed: {source_coverage.get('last_refreshed') or generated_at}",
                        ]
                    ),
                    small_style,
                ),
            ]
        )

        doc.build(story)
        buffer.seek(0)
        return buffer.read()

    def _render_industry_pdf_report(self, payload: dict[str, Any]) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=34,
            leftMargin=34,
            topMargin=34,
            bottomMargin=34,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "IndustryPdfTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=6,
        )
        subtitle_style = ParagraphStyle(
            "IndustryPdfSubtitle",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=11.5,
            textColor=colors.HexColor("#475569"),
            spaceAfter=2,
        )
        heading_style = ParagraphStyle(
            "IndustryPdfHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=14,
            textColor=colors.HexColor("#0f766e"),
            spaceBefore=8,
            spaceAfter=5,
        )
        body_style = ParagraphStyle(
            "IndustryPdfBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=11.5,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=4,
        )
        small_style = ParagraphStyle(
            "IndustryPdfSmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#64748b"),
        )

        def safe_text(value: Any, default: str = "N/A") -> str:
            text = str(value or "").strip()
            return text if text else default

        def safe_number(value: Any, default: float = 0.0, cap: float | None = None) -> float:
            try:
                number = float(value)
            except (TypeError, ValueError):
                number = default
            if cap is not None:
                number = min(number, cap)
            return number

        def report_type(data: dict[str, Any]) -> str:
            context = str(
                data.get("report_type")
                or data.get("context_type")
                or data.get("active_type")
                or data.get("analysis_type")
                or data.get("mode")
                or ""
            ).strip().lower()
            if context in {"search", "search-intelligence"} or data.get("query"):
                return "search"
            if context in {"compare", "comparison", "competitor"} or (data.get("q1") and data.get("q2")):
                return "compare"
            if context in {"trend", "trend-intelligence"} or data.get("trend_name") or data.get("trend"):
                return "trend"
            if context in {"product-impact", "product impact", "launch", "launch-readiness"} or data.get("feature_name"):
                return "product-impact"
            return "snapshot"

        def p(text: Any, style=body_style) -> Paragraph:
            return Paragraph(self._escape(text or "N/A"), style)

        def bullet_text(items: list[Any]) -> Paragraph:
            cleaned = [str(item).strip() for item in items if str(item or "").strip()]
            return Paragraph(
                "<br/>".join(f"- {self._escape(item)}" for item in cleaned[:6]) if cleaned else "N/A",
                body_style,
            )

        def news_row(item: Any) -> list[Any]:
            if isinstance(item, dict):
                title = safe_text(item.get("title") or item.get("headline") or item.get("name") or item.get("summary"), "News item")
                source = safe_text(item.get("source") or item.get("publisher") or item.get("source_name"), "Source")
                date_value = safe_text(item.get("published_date") or item.get("date") or item.get("published_at"), "")
                url = safe_text(item.get("url") or item.get("link"), "")
                if url and url != "N/A":
                    title_html = f'<a href="{self._escape(url)}" color="#0f766e">{self._escape(title)}</a>'
                else:
                    title_html = self._escape(title)
                return [Paragraph(title_html, body_style), Paragraph(self._escape(f"{source} • {date_value}".strip(" •")), body_style)]
            return [p(item), p("")]

        def history_rows(history: Any) -> list[list[Any]]:
            source_items = []
            if isinstance(history, dict):
                source_items = history.get("history") or []
            elif isinstance(history, list):
                source_items = history
            rows: list[list[Any]] = []
            for item in source_items[:6]:
                if not isinstance(item, dict):
                    continue
                rows.append([
                    p(item.get("timestamp"), small_style),
                    p(f"{safe_number(item.get('trend_score')):.0f}"),
                    p(f"{safe_number(item.get('growth_score')):.0f}"),
                    p(f"{safe_number(item.get('confidence_score')):.0f}"),
                ])
            return rows

        def t(headers: list[str], rows: list[list[Any]], widths: list[float]) -> Table:
            data = [[Paragraph(f"<b>{self._escape(h)}</b>", body_style) for h in headers]]
            data.extend(rows)
            table = Table(data, colWidths=widths, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcfce7")),
                        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                        ("LEADING", (0, 0), (-1, -1), 10.5),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#f8fafc")]),
                    ]
                )
            )
            return table

        def heading(text: str) -> Paragraph:
            return Paragraph(self._escape(text), heading_style)

        def build_horizontal_chart(labels: list[str], values: list[int], title: str, value_label: str) -> Drawing:
            width = 500
            height = max(120, 24 * max(3, len(labels)) + 20)
            drawing = Drawing(width, height)
            drawing.add(String(0, height - 12, title, fontName="Helvetica-Bold", fontSize=9.5, fillColor=colors.HexColor("#334155")))
            chart = HorizontalBarChart()
            chart.x = 120
            chart.y = 18
            chart.height = height - 42
            chart.width = width - 150
            chart.data = [values or [0]]
            chart.barWidth = 10
            chart.groupSpacing = 8
            chart.categoryAxis.categoryNames = labels or ["N/A"]
            chart.categoryAxis.labels.boxAnchor = "e"
            chart.categoryAxis.labels.fontName = "Helvetica"
            chart.categoryAxis.labels.fontSize = 8
            chart.categoryAxis.labels.fillColor = colors.HexColor("#334155")
            chart.categoryAxis.visibleGrid = False
            chart.valueAxis.valueMin = 0
            chart.valueAxis.valueMax = 100
            chart.valueAxis.valueStep = 20
            chart.valueAxis.labels.fontName = "Helvetica"
            chart.valueAxis.labels.fontSize = 8
            chart.bars[0].fillColor = colors.HexColor("#10b981")
            drawing.add(chart)
            drawing.add(String(390, 6, value_label, fontName="Helvetica", fontSize=7.5, fillColor=colors.HexColor("#64748b")))
            return drawing

        data = payload or {}
        kind = report_type(data)
        source_coverage = data.get("source_coverage") or {}
        generated_at = data.get("generated_at") or data.get("last_updated") or datetime.now(timezone.utc).isoformat()
        generated_text = generated_at.isoformat() if isinstance(generated_at, datetime) else str(generated_at)

        title_map = {
            "search": "Search Intelligence Report",
            "compare": "Competitor Intelligence Report",
            "trend": "Trend Intelligence Report",
            "product-impact": "Executive Launch Readiness Report",
            "snapshot": "Latest Intelligence Snapshot",
        }
        subtitle_map = {
            "search": f"Current query: {safe_text(data.get('query'))}",
            "compare": f"Comparison: {safe_text(data.get('q1'))} vs {safe_text(data.get('q2'))}",
            "trend": f"Trend focus: {safe_text(data.get('trend_name') or data.get('trend'))}",
            "product-impact": f"Feature: {safe_text(data.get('feature_name'))}",
            "snapshot": "Executive snapshot of the current Industry Intelligence state.",
        }

        story: list[Any] = [
            Paragraph(f"Enterprise AI {title_map[kind]}", title_style),
            Paragraph(subtitle_map[kind], subtitle_style),
            Paragraph(f"Generated: {self._escape(generated_text)}", subtitle_style),
            Spacer(1, 0.12 * inch),
        ]

        if kind == "search":
            history = data.get("trend_history") or data.get("history") or {}
            search_recommendations = data.get("recommendations") or [data.get("recommended_action") or data.get("executive_summary") or data.get("summary")]
            executive_summary = data.get("executive_summary") or data.get("summary") or "Search intelligence for the selected query."
            business_impact = data.get("business_impact") or data.get("why_it_matters")
            search_recommendation_items = []
            for item in search_recommendations[:5]:
                if isinstance(item, dict):
                    search_recommendation_items.append(item.get("recommended_action") or item.get("recommendation") or item.get("why_it_matters"))
                else:
                    search_recommendation_items.append(item)
            search_recommendation_items = [str(item).strip() for item in search_recommendation_items if str(item or "").strip()]
            if not search_recommendation_items:
                search_recommendation_items = [data.get("recommended_action") or data.get("executive_summary") or "Use the topic as an enterprise buying signal."]
            story.extend(
                [
                    heading("Executive Insight"),
                    p(executive_summary),
                    *( [p(business_impact, body_style)] if business_impact else [] ),
                    heading("Key Metrics"),
                    t(
                        ["Metric", "Value"],
                        [
                            [p("Query"), p(safe_text(data.get("query")))],
                            [p("Trend Score"), p(f"{safe_number(data.get('trend_score')):.0f} / 100")],
                            [p("Confidence"), p(f"{safe_number(data.get('confidence_score')):.0f}%")],
                            [p("Evidence Count"), p(f"{safe_number(data.get('evidence_count') or data.get('article_count') or 0):.0f}")],
                            [p("Source Count"), p(f"{safe_number(data.get('source_count')):.0f}")],
                            [p("Momentum"), p(safe_text(data.get("momentum"), "Stable"))],
                            [p("Growth Score"), p(f"{safe_number(data.get('growth_score')):.0f}%")],
                            [p("Last Updated"), p(safe_text(data.get("last_updated") or data.get("timestamp")))],
                            [p("Confidence Reason"), p(safe_text(data.get("confidence_reason") or "Evidence-backed from live signals."))],
                        ],
                        [1.4 * inch, 5.1 * inch],
                    ),
                    heading("Related Keywords"),
                    bullet_text(data.get("related_keywords") or []),
                    heading("Recent News"),
                    t(["Title", "Source / Date"], [news_row(item) for item in (data.get("recent_news") or [])[:5]] or [[p("No recent news found."), p("")]], [4.7 * inch, 1.8 * inch]),
                    heading("Recommendations"),
                    bullet_text(search_recommendation_items),
                    heading("Trend History"),
                    t(["Timestamp", "Trend", "Growth", "Conf."], history_rows(history) or [[p("No history available"), p("-"), p("-"), p("-")]], [2.3 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch]),
                ]
            )
        elif kind == "compare":
            confidence_value = data.get("confidence_score") or data.get("confidence") or data.get("trend_score")
            gap_analysis = data.get("competitive_gap_analysis") or {}
            strategic_recommendations = data.get("strategic_recommendations") or []
            action_plan = data.get("executive_action_plan") or {}
            roadmap = data.get("roadmap_30_60_90") or {}
            forecast = data.get("business_impact_forecast") or {}
            readiness = data.get("executive_readiness_score") or {}
            board_recommendations = data.get("board_recommendations") or []
            left_label = safe_text(gap_analysis.get("left_label") or data.get("q1"), "Left signal")
            right_label = safe_text(gap_analysis.get("right_label") or data.get("q2"), "Right signal")
            story.extend(
                [
                    heading("Executive Summary"),
                    p(data.get("executive_summary") or "Competitive comparison for the selected companies."),
                    heading("Comparison Metrics"),
                    t(
                        ["Metric", "Value"],
                        [
                            [p("Compared Companies"), p(f"{safe_text(data.get('q1'), 'Company 1')} vs {safe_text(data.get('q2'), 'Company 2')}")],
                            [p("Trend Score"), p(f"{safe_number(data.get('trend_score')):.0f} / 100")],
                            [p("Confidence"), p(f"{safe_number(confidence_value):.0f}%")],
                            [p("Evidence Count"), p(f"{safe_number(data.get('evidence_count') or 0):.0f}")],
                            [p("Source Count"), p(f"{safe_number(data.get('source_count')):.0f}")],
                            [p("Momentum"), p(safe_text(data.get("momentum"), "Moderate"))],
                            [p("Last Updated"), p(safe_text(data.get("last_updated") or data.get("timestamp")))],
                            [p("Confidence Reason"), p(safe_text(data.get("confidence_reason") or "Evidence-backed from live signals."))],
                        ],
                        [1.8 * inch, 4.7 * inch],
                    ),
                    heading("Keyword Overlap"),
                    bullet_text(data.get("keyword_overlap") or []),
                    heading("Strengths"),
                    bullet_text(data.get("strengths") or []),
                    heading("Weaknesses"),
                    bullet_text(data.get("weaknesses") or []),
                    heading("Competitive Gap Analysis"),
                    bullet_text([
                        f"{left_label} Wins: {', '.join(gap_analysis.get('left_wins') or [])}" if gap_analysis.get("left_wins") else f"{left_label} Wins: none identified",
                        f"{right_label} Wins: {', '.join(gap_analysis.get('right_wins') or [])}" if gap_analysis.get("right_wins") else f"{right_label} Wins: none identified",
                        f"Missing Capabilities: {', '.join(gap_analysis.get('missing_capabilities') or [])}" if gap_analysis.get("missing_capabilities") else "Missing Capabilities: none identified",
                        f"Market Positioning Gaps: {', '.join(gap_analysis.get('market_positioning_gaps') or [])}" if gap_analysis.get("market_positioning_gaps") else "Market Positioning Gaps: none identified",
                        f"Enterprise Readiness Gaps: {', '.join(gap_analysis.get('enterprise_readiness_gaps') or [])}" if gap_analysis.get("enterprise_readiness_gaps") else "Enterprise Readiness Gaps: none identified",
                    ]),
                    heading("Strategic Recommendations"),
                    bullet_text([
                        f"{item.get('priority', 'Priority')}: {item.get('initiative', '')} - {item.get('business_impact', '')}"
                        for item in strategic_recommendations
                        if isinstance(item, dict)
                    ] or [
                        "Position governance, compliance, and enterprise controls as the differentiator.",
                    ]),
                    heading("Executive Action Plan"),
                    bullet_text([
                        f"Immediate: {item.get('objective', '')} ({item.get('priority', 'Priority')})"
                        for item in action_plan.get("immediate_actions", [])
                        if isinstance(item, dict)
                    ] + [
                        f"Next: {item.get('objective', '')} ({item.get('priority', 'Priority')})"
                        for item in action_plan.get("next_actions", [])
                        if isinstance(item, dict)
                    ] + [
                        f"Long-Term: {item.get('objective', '')} ({item.get('priority', 'Priority')})"
                        for item in action_plan.get("long_term_actions", [])
                        if isinstance(item, dict)
                    ] or ["No action plan available."]),
                    heading("30 / 60 / 90 Day Roadmap"),
                    bullet_text([
                        f"30 Days: {item.get('objective', '')} ({item.get('priority', 'Priority')})"
                        for item in roadmap.get("30_days", [])
                        if isinstance(item, dict)
                    ] + [
                        f"60 Days: {item.get('objective', '')} ({item.get('priority', 'Priority')})"
                        for item in roadmap.get("60_days", [])
                        if isinstance(item, dict)
                    ] + [
                        f"90 Days: {item.get('objective', '')} ({item.get('priority', 'Priority')})"
                        for item in roadmap.get("90_days", [])
                        if isinstance(item, dict)
                    ] or ["No roadmap available."]),
                    heading("Business Impact Forecast"),
                    t(
                        ["Metric", "Value"],
                        [
                            [p("Market Visibility Gain"), p(f"+{safe_number(forecast.get('market_visibility_gain')):.0f}%")],
                            [p("Buyer Trust Gain"), p(f"+{safe_number(forecast.get('buyer_trust_gain')):.0f}%")],
                            [p("Competitive Advantage Gain"), p(f"+{safe_number(forecast.get('competitive_advantage_gain')):.0f}%")],
                            [p("Enterprise Adoption Impact"), p(f"+{safe_number(forecast.get('enterprise_adoption_impact')):.0f}%")],
                        ],
                        [2.6 * inch, 3.9 * inch],
                    ),
                    heading("Executive Readiness Score"),
                    t(
                        ["Readiness", "Score"],
                        [
                            [p("Governance"), p(f"{safe_number(readiness.get('governance_readiness')):.0f} / 100")],
                            [p("Compliance"), p(f"{safe_number(readiness.get('compliance_readiness')):.0f} / 100")],
                            [p("Security"), p(f"{safe_number(readiness.get('security_readiness')):.0f} / 100")],
                            [p("Enterprise"), p(f"{safe_number(readiness.get('enterprise_readiness')):.0f} / 100")],
                            [p("Overall"), p(f"{safe_number(readiness.get('overall_executive_readiness_score')):.0f} / 100")],
                        ],
                        [2.2 * inch, 4.3 * inch],
                    ),
                    heading("Board Recommendations"),
                    bullet_text([
                        f"{item.get('focus', 'Board')}: {item.get('recommendation', '')}"
                        for item in board_recommendations
                        if isinstance(item, dict)
                    ] or [
                        "Lead with governance, compliance, and audit evidence to convert interest into trust.",
                    ]),
                    heading("Recent News"),
                    t(["Title", "Source / Date"], [news_row(item) for item in (data.get("recent_news") or [])[:5]] or [[p("No recent news found."), p("")]], [4.7 * inch, 1.8 * inch]),
                    heading("Recommendations"),
                    bullet_text(
                        data.get("recommendations")
                        or [
                            f"Position {safe_text(data.get('q1'), 'Company 1')} against governance, security, and deployment readiness.",
                            f"Use {safe_text((data.get('keyword_overlap') or ['enterprise ai'])[0], 'enterprise AI')} as the anchor theme for the executive narrative.",
                        ]
                    ),
                ]
            )
        elif kind == "trend":
            confidence_value = data.get("confidence_score") or data.get("confidence") or data.get("trend_score")
            history = data.get("trend_history") or data.get("history") or {}
            story.extend(
                [
                    heading("Executive Summary"),
                    p(data.get("executive_summary") or data.get("summary") or "Trend intelligence for the selected topic."),
                    heading("Trend Metrics"),
                    t(
                        ["Metric", "Value"],
                        [
                            [p("Trend Name"), p(safe_text(data.get("trend_name") or data.get("trend")))],
                            [p("Trend Score"), p(f"{safe_number(data.get('trend_score')):.0f} / 100")],
                            [p("Confidence"), p(f"{safe_number(confidence_value):.0f}%")],
                            [p("Evidence Count"), p(f"{safe_number(data.get('evidence_count') or data.get('article_count') or 0):.0f}")],
                            [p("Source Count"), p(f"{safe_number(data.get('source_count')):.0f}")],
                            [p("Momentum"), p(safe_text(data.get("momentum"), "Stable"))],
                            [p("Last Updated"), p(safe_text(data.get("last_updated") or data.get("timestamp")))],
                            [p("Confidence Reason"), p(safe_text(data.get("confidence_reason") or "Evidence-backed from live signals."))],
                        ],
                        [1.8 * inch, 4.7 * inch],
                    ),
                    heading("Keywords"),
                    bullet_text(data.get("keywords") or data.get("related_keywords") or []),
                    heading("News"),
                    t(["Title", "Source / Date"], [news_row(item) for item in (data.get("recent_news") or [])[:5]] or [[p("No recent news found."), p("")]], [4.7 * inch, 1.8 * inch]),
                    heading("Opportunities"),
                    bullet_text([
                        item.get("opportunity_name") or item.get("title") or item.get("summary")
                        for item in (data.get("opportunities") or [])[:5]
                        if isinstance(item, dict)
                    ]),
                    heading("Trend History"),
                    t(["Timestamp", "Trend", "Growth", "Conf."], history_rows(history) or [[p("No history available"), p("-"), p("-"), p("-")]], [2.3 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch]),
                ]
            )
        elif kind == "product-impact":
            executive_verdict = data.get("executive_verdict") or {}
            key_scores = data.get("key_scores") or {}
            ml_predictions = data.get("ml_predictions") or {}
            contributing_factors = data.get("top_contributing_factors") or {}
            top_opportunities = [item for item in (data.get("top_opportunities") or []) if isinstance(item, dict)]
            top_risks = [item for item in (data.get("top_risks") or []) if isinstance(item, dict)]
            next_actions = data.get("recommended_next_actions") or {}
            report_summary = (
                executive_verdict.get("explanation")
                or data.get("executive_launch_readiness_report")
                or "Executive decision support for the selected feature."
            )
            confidence_score = safe_number(executive_verdict.get("confidence_score") or data.get("confidence_score"))
            verdict_label = safe_text(executive_verdict.get("verdict") or data.get("recommended_launch_priority"), "Validate First")
            launch_prediction = ml_predictions.get("launch_readiness") or {}
            risk_prediction = ml_predictions.get("risk_classification") or {}
            revenue_prediction = ml_predictions.get("revenue_opportunity") or {}
            launch_factors = contributing_factors.get("launch_readiness") or []
            risk_factors = contributing_factors.get("risk_classification") or []
            revenue_factors = contributing_factors.get("revenue_opportunity") or []
            def factor_line(items: list[dict[str, Any]] | list[Any]) -> str:
                parts = []
                for item in items[:3]:
                    if isinstance(item, dict):
                        signed = str(item.get("signed_display") or "").strip()
                        if not signed:
                            signed_value = safe_number(item.get("signed_impact") or item.get("impact") or 0.0)
                            signed = f"{signed_value:+.2f}"
                        direction = str(item.get("contribution_direction") or item.get("direction") or "Positive").strip()
                        explanation = str(item.get("business_explanation") or "").strip()
                        fragment = f"{signed} {item.get('factor') or 'Factor'} | Contribution Direction: {direction}"
                        if explanation:
                            fragment = f"{fragment} | Business Explanation: {explanation}"
                        parts.append(fragment)
                return " ; ".join(parts) if parts else "No factor data"
            key_score_rows = [
                ["Market Demand", f"{safe_number(key_scores.get('market_demand') or data.get('market_demand_score')):.0f} / 100"],
                ["Enterprise Fit", f"{safe_number(key_scores.get('enterprise_fit') or data.get('enterprise_fit_score') or data.get('strategic_fit_score')):.0f} / 100"],
                ["Revenue Opportunity", f"{safe_number(key_scores.get('revenue_opportunity') or data.get('revenue_opportunity_score')):.0f} / 100"],
                ["Competitive Advantage", f"{safe_number(key_scores.get('competitive_advantage') or data.get('competitive_advantage_score')):.0f} / 100"],
                ["Risk", f"{safe_number(key_scores.get('risk') or data.get('risk_score')):.0f} / 100"],
                ["Launch Readiness", f"{safe_number(key_scores.get('launch_readiness') or data.get('overall_launch_readiness_score')):.0f} / 100"],
            ]
            opportunity_rows = [
                f"{item.get('opportunity') or item.get('title') or 'Opportunity'} - {item.get('business_impact') or item.get('summary') or ''}"
                for item in top_opportunities[:3]
            ]
            risk_rows = [
                f"{item.get('risk') or item.get('title') or 'Risk'} - {item.get('mitigation') or item.get('summary') or ''}"
                for item in top_risks[:3]
            ]
            immediate_actions = next_actions.get("immediate_actions") or []
            short_term_actions = next_actions.get("short_term_actions") or []
            launch_actions = next_actions.get("launch_actions") or []
            story.extend(
                [
                    heading("Executive Verdict"),
                    p(report_summary),
                    heading("Decision"),
                    t(
                        ["Metric", "Value"],
                        [
                            [p("Verdict"), p(verdict_label)],
                            [p("Confidence"), p(f"{confidence_score:.0f}%")],
                            [p("Feature"), p(safe_text(data.get("feature_name")))],
                        ],
                        [1.8 * inch, 4.7 * inch],
                    ),
                    heading("Key Scores"),
                    t(["Metric", "Value"], key_score_rows, [2.2 * inch, 4.3 * inch]),
                    heading("ML Predictions"),
                    bullet_text([
                        f"Launch readiness: {safe_number(launch_prediction.get('predicted_score') or data.get('predicted_launch_readiness_score') or data.get('overall_launch_readiness_score')):.0f}/100 with {safe_number(launch_prediction.get('confidence_score') or data.get('prediction_confidence')):.0f}% confidence.",
                        f"Risk classification: {safe_text(risk_prediction.get('predicted_label') or data.get('risk_classification_label'), 'Medium Risk')} at {safe_number(risk_prediction.get('risk_probability') or data.get('predicted_risk_probability')):.2f} probability.",
                        f"Revenue opportunity: {safe_number(revenue_prediction.get('predicted_score') or data.get('predicted_revenue_opportunity_score') or data.get('revenue_opportunity_score')):.0f}/100 with {safe_number(revenue_prediction.get('confidence_score') or data.get('prediction_confidence')):.0f}% confidence.",
                    ]),
                    heading("Top Contributing Factors"),
                    bullet_text([
                        f"Launch readiness: {factor_line(launch_factors)}",
                        f"Risk: {factor_line(risk_factors)}",
                        f"Revenue: {factor_line(revenue_factors)}",
                    ]),
                    heading("Top Opportunities"),
                    bullet_text([
                        item
                        for item in opportunity_rows[:3]
                        if str(item or "").strip()
                    ] or ["No major opportunities identified."],),
                    heading("Top Risks"),
                    bullet_text([
                        item
                        for item in risk_rows[:3]
                        if str(item or "").strip()
                    ] or ["No material risks identified."],),
                    heading("Recommended Next Actions"),
                    bullet_text([
                        f"Immediate: {', '.join(str(item) for item in immediate_actions[:3] if str(item or '').strip())}" if immediate_actions else "Immediate: validate the buyer problem and launch owner.",
                        f"30 Days: {', '.join(str(item) for item in short_term_actions[:3] if str(item or '').strip())}" if short_term_actions else "30 Days: tighten positioning and pilot scope.",
                        f"60-90 Days: {', '.join(str(item) for item in launch_actions[:3] if str(item or '').strip())}" if launch_actions else "60-90 Days: launch only after the pilot proves pull.",
                    ]),
                    heading("Final Recommendation"),
                    p(safe_text(data.get("final_recommendation") or report_summary)),
                ]
            )
        else:
            top_trends = data.get("top_trends") or []
            opportunities = data.get("opportunities") or []
            risks = data.get("strategic_risks") or data.get("top_risks") or []
            recommendations = data.get("recommendations") or data.get("executive_recommendations") or []
            executive = data.get("executive_summary") or {}
            risk_items = []
            for item in risks[:5]:
                if isinstance(item, dict):
                    risk_items.append(
                        item.get("risk")
                        or item.get("risk_summary")
                        or item.get("summary")
                        or item.get("title")
                        or item.get("why_it_matters")
                    )
                else:
                    risk_items.append(item)
            if not risk_items:
                risk_items = [data.get("main_risk") or executive.get("main_risk") or "Enterprise AI adoption is outpacing governance controls."]
            risk_items = [str(item).strip() for item in risk_items if str(item or "").strip()]
            if not risk_items:
                risk_items = ["Enterprise AI adoption is outpacing governance controls."]
            story.extend(
                [
                    heading("Executive Summary"),
                    p(
                        " | ".join(
                            [
                                f"Top signal: {executive.get('top_signal') or 'N/A'}",
                                f"Main opportunity: {executive.get('main_opportunity') or 'N/A'}",
                                f"Main risk: {executive.get('main_risk') or 'N/A'}",
                                f"Recommended action: {executive.get('recommended_action') or 'N/A'}",
                            ]
                        )
                    ),
                    heading("Top Trends"),
                    t(
                        ["Trend", "Score", "Direction"],
                        [
                            [
                                p(safe_text(item.get("trend_name") or item.get("title"), "Trend")),
                                p(f"{safe_number(item.get('trend_score') or item.get('momentum_score')):.0f}"),
                                p(safe_text(item.get("direction") or item.get("signal_strength"), "Stable")),
                            ]
                            for item in top_trends[:5]
                            if isinstance(item, dict)
                        ] or [[p("No trends available"), p("-"), p("-")]],
                        [3.0 * inch, 1.0 * inch, 2.0 * inch],
                    ),
                    heading("Top Opportunities"),
                    bullet_text([
                        item.get("opportunity_name") or item.get("title") or item.get("summary")
                        for item in opportunities[:5]
                        if isinstance(item, dict)
                    ]),
                    heading("Top Risks"),
                    bullet_text(risk_items),
                    heading("Executive Recommendations"),
                    bullet_text([
                        item.get("trend") or item.get("insight_title") or item.get("recommendation")
                        for item in recommendations[:5]
                        if isinstance(item, dict)
                    ]),
                ]
            )

        if kind == "search":
            story.extend(
                [
                    heading("Executive Implications"),
                    bullet_text([
                        f"{safe_text(data.get('query'))} is attracting enterprise attention because {safe_text(data.get('executive_summary') or data.get('summary') or 'the market is actively evaluating the signal').lower()}.",
                        f"Confidence is capped at {safe_number(data.get('confidence_score') or data.get('confidence') or data.get('trend_score')):.0f}% and should be read alongside news volume and keyword fit.",
                        "Use the topic as a customer-facing wedge by pairing the signal with governance, security, or compliance proof points.",
                    ]),
                    heading("Decision Summary"),
                    p("The near-term move is to connect this signal to an enterprise buying motion and use the trend history to show whether momentum is rising, stable, or cooling."),
                ]
            )
        elif kind == "compare":
            compare_recommendations = data.get("recommendations") or [
                f"Position {safe_text(data.get('q1'), 'Company 1')} against governance, security, and deployment readiness.",
                f"Use {safe_text((data.get('keyword_overlap') or ['enterprise ai'])[0], 'enterprise AI')} as the anchor theme for the executive narrative.",
            ]
            story.extend(
                [
                    heading("Recommendations"),
                    bullet_text(compare_recommendations),
                    heading("Executive Implications"),
                    bullet_text([
                        f"{safe_text(data.get('q1'), 'Company 1')} appears stronger when the board cares most about momentum and visibility.",
                        f"The shared theme is {safe_text((data.get('keyword_overlap') or ['enterprise ai'])[0], 'enterprise AI')}, which keeps the comparison anchored in enterprise buying criteria.",
                        "Position the weaker side against governance, security, and deployment readiness to make the comparison commercially useful.",
                    ]),
                    heading("Decision Summary"),
                    p("Use the comparison to sharpen positioning, strengthen differentiation, and decide which proof points should lead the next executive narrative."),
                    heading("Strategic Narrative"),
                    p("The board lens here is not just who is louder, but which company is most credible when the buyer wants enterprise control and operational readiness."),
                    p("Use the overlap theme to keep the message aligned with enterprise AI, trust, and deployment depth."),
                    heading("Board Takeaway"),
                    bullet_text([
                        "Anchor the comparison in the buyer problem, not the product category.",
                        "Translate the stronger signal into a narrative the sales team can repeat.",
                        "Use governance, security, and proof of execution as the differentiators.",
                    ]),
                ]
            )
        elif kind == "trend":
            story.extend(
                [
                    heading("Executive Implications"),
                    bullet_text([
                        f"{safe_text(data.get('trend_name') or data.get('trend'))} is the primary signal and should be tracked against governance and risk controls.",
                        f"Current momentum of {safe_text(data.get('momentum'), 'Stable')} suggests the topic is still usable for near-term executive storytelling.",
                        "Translate the trend into a customer action by tying it to a buyer problem, a proof point, and a short implementation horizon.",
                    ]),
                    heading("Decision Summary"),
                    p("The trend is most valuable when it becomes a concrete enterprise use case with a clear owner, timeline, and commercial outcome."),
                    heading("Trend Narrative"),
                    p("Use the trend history to distinguish a short-term spike from a durable enterprise signal."),
                    p("When the topic keeps rising across news, keywords, and competitor mentions, it is ready for a go-to-market motion."),
                ]
            )
        elif kind == "snapshot":
            risk_items = []
            for item in risks[:5]:
                if isinstance(item, dict):
                    risk_items.append(
                        item.get("risk")
                        or item.get("risk_summary")
                        or item.get("summary")
                        or item.get("title")
                        or item.get("why_it_matters")
                    )
                else:
                    risk_items.append(item)
            if not risk_items:
                risk_items = [data.get("main_risk") or data.get("executive_summary", {}).get("main_risk") or "Enterprise AI adoption is outpacing governance controls."]
            risk_items = [str(item).strip() for item in risk_items if str(item or "").strip()]
            if not risk_items:
                risk_items = ["Enterprise AI adoption is outpacing governance controls."]
            story.extend(
                [
                    heading("Executive Implications"),
                    bullet_text([
                        "The snapshot shows which signals are strongest right now and which topics should be converted into board-level language.",
                        "Use the opportunity list to choose the next commercial wedge, then align risk and governance messaging around it.",
                        "Use the top risks list to avoid generic AI messaging and keep the strategy grounded in enterprise control and proof.",
                    ]),
                    heading("Decision Summary"),
                    p("The best next move is to prioritize the strongest signal, convert it into a buyer-facing story, and keep the narrative tied to enterprise adoption and risk reduction."),
                    heading("Market Narrative"),
                    p("This snapshot is the executive starting point for the current market pulse and should anchor the next board discussion."),
                    p("The goal is to keep the conversation focused on enterprise AI control, trust, and commercial readiness rather than broad technology noise."),
                    heading("Source Coverage"),
                    bullet_text([
                        f"Giggso Website: {source_coverage.get('company') or 'Available'}",
                        f"LinkedIn: {source_coverage.get('linkedin') or 'Available'}",
                        f"News: {source_coverage.get('news') or 'Available'}",
                        f"Competitors: {source_coverage.get('competitors') or 'Available'}",
                        f"AI Insights: {source_coverage.get('insights') or 'Fallback'}",
                        f"Last Refreshed: {source_coverage.get('last_refreshed') or generated_text}",
                    ]),
                    heading("Board Summary"),
                    bullet_text([
                        "Prioritize the highest-signal trend and convert it into a customer-facing proof point.",
                        "Use the opportunity list to guide next-quarter commercial focus.",
                        "Treat the risk list as the guardrail for all executive messaging.",
                    ]),
                ]
            )

        doc.build(story)
        buffer.seek(0)
        return buffer.read()

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
