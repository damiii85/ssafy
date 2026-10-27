"""주소가 없는 첫 업종 질문에도 전체 수집본으로 현황을 설명한다."""
import pandas as pd

from src.services.pilot_report import CATEGORY_FIELDS
from src.services.spot_catalog import get_spot
from src.services.pdf_evidence import local_pdf_answer

# 서비스의 일반 업종 안내. 지역 현황이나 공공기관의 공식 정의로 인용하지 않는다.
GUIDES = {
    "카페": "커피·차 등 음료를 중심으로 판매하는 매장입니다. 좌석과 체류 중심인지, 포장 판매 중심인지에 따라 비교할 경쟁 점포와 필요한 위치가 달라질 수 있어요.",
    "미용실": "커트·염색·스타일링 등 모발 관련 서비스를 제공하는 매장입니다. 제공할 시술과 목표 고객을 정한 뒤 같은 생활권의 경쟁 점포를 비교하는 것이 좋습니다.",
    "네일숍": "손발톱 관리와 미용 서비스를 제공하는 매장입니다. 예약 운영 방식과 제공할 시술 범위를 정해 주변 동종 매장과 비교해 볼 수 있어요.",
    "편의점": "식품과 생활용품 등을 판매하는 소매 매장입니다. 주변의 같은 업종뿐 아니라 접근 동선과 운영 방식도 함께 살펴볼 필요가 있습니다.",
    "여성 의류 소매업": "여성 의류를 소비자에게 판매하는 소매 업종입니다. 가격대·상품 구성·목표 고객을 구체화하면 비교할 점포 범위를 좁힐 수 있어요.",
    "남성 의류 소매업": "남성 의류를 소비자에게 판매하는 소매 업종입니다. 상품과 가격대가 다른 점포를 모두 동일한 경쟁자로 보기보다 매장 구성을 함께 확인하는 것이 좋습니다.",
    "독서실/스터디 카페": "학습을 위한 공간을 제공하는 업종으로, 음료 판매 중심의 일반 카페와 구분해 집계합니다.",
    "음식": "조리한 음식 등을 판매하는 여러 세부 업종을 묶은 대분류입니다. 한식·중식 등 원하는 메뉴나 매장 형태를 알려주시면 범위를 더 좁힐 수 있어요.",
}


def industry_briefing(spot_id, stores, metadata, categories):
    spot = get_spot(spot_id)
    mask = pd.Series(False, index=stores.index)
    counts, taxonomy = [], []
    for category in categories:
        selected = stores[CATEGORY_FIELDS[category['level']]] == category['name']
        mask |= selected
        counts.append({"업종": category['name'], "점포 수": int(selected.sum())})
        for row in stores.loc[selected, ['indsLclsNm', 'indsMclsNm', 'indsSclsNm']].drop_duplicates().itertuples(index=False, name=None):
            taxonomy.append(" → ".join(row))
    matches = stores[mask].copy()
    names = ", ".join(c['name'] for c in categories)
    total, count = len(stores), len(matches)
    lines = [f"**{spot['name']}에서 {names} 창업을 생각하고 계시는군요. 업종과 지역 현황부터 살펴볼게요.**",
             "**어떤 업종인가요?**\n\n" + " ".join(GUIDES[c['name']] for c in categories if c['name'] in GUIDES)
             + f"\n\n상가정보 API에서 선택한 업종은 **{names}**이며, "
             + ("다음 분류에 속합니다: " + "; ".join(taxonomy[:5]) if taxonomy else "이번 수집본에서 일치하는 점포가 없습니다.") + ".",
             f"**이 지역의 해당 업종 현황**\n\n집계 범위: **{metadata.get('scope_description', spot['name'] + ' 수집 범위')}**. "
             f"확인된 전체 상가 **{total:,}곳** 중 해당 업종은 **{count:,}곳**"
             + (f" ({count / total:.1%})입니다." if total else '입니다. 범위 안에서 확인된 등록 상가가 없습니다.')]
    if len(categories) > 1:
        lines.append("업종별 집계: " + ", ".join(f"{r['업종']} {r['점포 수']:,}곳" for r in counts)
                     + ". 합계는 상가 ID 기준으로 중복을 제거했습니다.")
    lines.append(f"출처: [소상공인시장진흥공단 상가정보 API]({metadata['source']}) 수집본. "
                 f"원본 수집일 {', '.join(metadata.get('source_date_range', [metadata['collected_at_utc'][:10]]))}, 집계 범위는 위 기준입니다. "
                 "분류·현황의 출처는 API이며 점포 수는 수집 시점의 등록 정보입니다. 업종의 일반 설명과 확인 제안은 서비스 안내입니다.")
    lines.append(local_pdf_answer(spot_id, "지역 특징", summary=True))
    lines.append("**창업 판단 전에 확인할 점**\n\n위 PDF 수치는 상권 전체의 배경 자료이며 해당 업종의 매출·고객 수가 아닙니다. "
                 "업종별 매출·실제 임대료·방문 전환율은 알 수 없어 성공 가능성을 단정할 수 없습니다. "
                 "유동인구·교통·업종 구성이나 다른 지역의 같은 지표를 질문하시면 지역의 특성을 더 살펴볼 수 있어요.")
    report = {"type": "overview", "spot": spot['name'], "categories": categories,
              'region_id': spot_id, 'parent_id': spot.get('parent_id', spot_id),
              'scope_kind': metadata.get('scope_kind', 'region'), 'scope_center': metadata.get('scope_center', spot['name']),
              'scope_description': metadata.get('scope_description', spot['name'] + ' 수집 범위'),
              'source_dates': metadata.get('source_date_range', [metadata['collected_at_utc'][:10]]),
              "total_stores": total, "competitor_count": count, "category_counts": counts,
              "radius_m": metadata['radius_m'], "source": metadata['source'],
              "collected_at": metadata['collected_at_utc'],
              "distribution": {str(k): int(v) for k, v in matches.indsSclsNm.value_counts().items()},
              "all_distribution": {str(k): int(v) for k, v in stores.indsLclsNm.value_counts().items()}}
    for field in ('scope_latitude', 'scope_longitude', 'scope_coordinate_source'):
        if field in metadata:
            report[field] = metadata[field]
    return "\n\n".join(lines), report
