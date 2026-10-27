"""시각화에는 검증된 집계와 PDF의 동일 지표만 전달한다."""
from src.services.pdf_evidence import METRICS, UNITS, PDF_PATH, pdf_regions, report_data


def distribution_rows(distribution, limit=6):
    pairs = sorted(distribution.items(), key=lambda item: (-item[1], item[0]))
    rows = [{"업종": name.strip() or "미분류", "점포 수": int(count)} for name, count in pairs[:limit]]
    remainder = sum(count for _, count in pairs[limit:])
    if remainder:
        rows.append({"업종": "그 외 업종", "점포 수": int(remainder)})
    return rows


def pdf_visuals(spot_id, question, answer):
    """실제 답변에 명시적으로 출력된 값만 차트로 옮긴다."""
    rows = []
    try:
        for region in pdf_regions(spot_id, question):
            data = report_data(region)
            for metric, unit in zip(METRICS, UNITS):
                value = data['metrics'][metric]
                if f"{metric}: **{value:,}{unit}**" in answer:
                    rows.append({"지역": region, "지표": metric, "값": value, "단위": unit})
    except (OSError, ValueError, IndexError):
        return None
    return {"type": "pdf_metrics", "rows": rows, "source": PDF_PATH.name,
            "reference": "통계표 2쪽 · 기준연월 1·10쪽"} if rows else None


def public_report(report):
    """과거 세션의 주소·후보 목록을 화면/다운로드로 되살리지 않는다."""
    if not report or report.get('type') != 'overview':
        return None
    fields = ('type', 'spot', 'categories', 'total_stores', 'competitor_count', 'category_counts',
              'radius_m', 'source', 'collected_at', 'distribution', 'all_distribution', 'created_at',
              'region_id', 'parent_id', 'scope_kind', 'scope_center', 'scope_description', 'source_dates',
              'scope_latitude', 'scope_longitude', 'scope_coordinate_source')
    return {key: report[key] for key in fields if key in report}
