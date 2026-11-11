"""Comparable multi-quarter financial metrics, based only on existing saved evidence."""
import re
from collections import defaultdict
from app.schemas import AnalyzeResponse

def period_key(period: str) -> tuple[int, int, str]:
    years = re.findall(r"20\d{2}", period)
    quarters = re.search(r"(?:Q|quarter\s*)([1-4])", period, flags=re.I)
    return (int(years[0]) if years else 0, int(quarters.group(1)) if quarters else 0, period)

def compare_many(reports: list[AnalyzeResponse]) -> dict:
    if len(reports) < 2:
        raise ValueError("Select two or more reports")
    tickers = {r.ticker.upper() for r in reports}
    if len(tickers) != 1:
        raise ValueError("Multi-quarter comparisons require reports for the same company")
    reports = sorted(reports, key=lambda r: (period_key(r.fiscal_period), r.analyzed_at.isoformat()))
    if len({r.fiscal_period.strip().upper() for r in reports}) != len(reports):
        raise ValueError("Choose only one saved analysis for each fiscal period")
    columns = [{
        "analysis_id": r.analysis_id, "fiscal_period": r.fiscal_period,
        "announcement_date": r.announcement_date.isoformat() if r.announcement_date else None,
    } for r in reports]
    combined: dict[tuple, dict] = {}
    warnings = []
    for index, report in enumerate(reports):
        eligible = report.extraction_version >= 2 and (
            report.data_origin != 'sec_filing' or report.extraction_version >= 3)
        if not eligible:
            warnings.append(f"{report.fiscal_period}: older extraction version; figures withheld until reanalyzed")
            continue
        for metric in report.metrics:
            if metric.extraction_status != 'extracted' or metric.normalized_value is None:
                continue
            key = (metric.name.lower(), metric.unit, metric.currency, metric.metric_variant)
            item = combined.setdefault(key, {
                "name": metric.name, "unit": metric.unit, "currency": metric.currency,
                "metric_variant": metric.metric_variant, "values": [None] * len(reports),
                "evidence": [None] * len(reports),
            })
            item["values"][index] = metric.normalized_value
            item["evidence"][index] = metric.evidence.model_dump()
    metrics = []
    narratives = []
    for key, item in sorted(combined.items()):
        present = [(i, v) for i, v in enumerate(item["values"]) if v is not None]
        item["available_periods"] = len(present)
        item["change_percent"] = None
        if len(present) >= 2:
            first_i, first_v = present[0]
            last_i, last_v = present[-1]
            if first_v != 0:
                pct = round((last_v / first_v - 1) * 100, 2)
                item["change_percent"] = pct
                direction = "rose" if pct > 0 else "fell" if pct < 0 else "was unchanged"
                narratives.append(
                    f"{item['name']} {direction} {abs(pct):.1f}% between "
                    f"{reports[first_i].fiscal_period} and {reports[last_i].fiscal_period} "
                    f"({len(present)}/{len(reports)} periods have comparable data)."
                )
        metrics.append(item)
    if not metrics:
        warnings.append("No compatible validated metric values across these selected quarters")
    warnings.append("A change between selected periods is not necessarily quarter-over-quarter growth.")
    warnings.append("Missing values are not estimated or interpolated; confirm units and cited passages.")
    return {
        "ticker": reports[0].ticker, "company_name": reports[0].company_name,
        "periods": columns, "metrics": metrics,
        "narrative": narratives[:8], "warnings": warnings,
    }
