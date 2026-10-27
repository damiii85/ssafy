"""수집본에서 스팟별 업종 분포와 데이터 목록을 생성한다."""

import json
from pathlib import Path

import pandas as pd

from src.services.spot_catalog import BASE_DIR, load_spots, data_paths, inventory
from src.services.pilot_report import load_spot_data


def export_summaries():
    from src.services.pdf_evidence import PDF_PATH, REGIONS
    overview = []
    for spot in load_spots():
        if not all(path.exists() for path in data_paths(spot["id"])):
            continue
        df, metadata = load_spot_data(spot["id"])
        directory = BASE_DIR / "data/processed/spots" / spot["id"]
        directory.mkdir(parents=True, exist_ok=True)
        categories = df.groupby(["indsLclsNm", "indsMclsNm", "indsSclsNm"]).size().reset_index(name="store_count")
        categories = categories.sort_values("store_count", ascending=False)
        categories.to_csv(directory / "category_counts.csv", index=False, encoding="utf-8-sig")
        summary = {"spot": spot, "count": len(df), "metadata": metadata,
                   "raw_csv": str(data_paths(spot["id"])[0].relative_to(BASE_DIR)),
                   "category_count": len(categories), "top_categories": categories.head(10).to_dict(orient="records"),
                   "sales": "미확보", "foot_traffic": "미확보", "rent": "미확보",
                   "external_reports": [{'file': str(PDF_PATH.relative_to(BASE_DIR)),
                                         'pages': list(REGIONS.get(spot['name'], ())),
                                         'statistics_page': 2, 'reference_pages': [1, 10]}] if PDF_PATH.exists() else [],
                   "document_search_queries": [f"대구 {spot['name']} 상권 분석 보고서 소비 업종",
                                               f"대구 {spot['name']} 공실 임대 동향"]}
        (directory / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        overview.append({"spot_id": spot["id"], "스팟": spot["name"], "구": spot["district"],
                         "상가 수": len(df), "소분류 수": len(categories), "수집일": metadata["collected_at_utc"][:10]})
    output = BASE_DIR / "data/processed/spots"
    pd.DataFrame(overview).to_csv(output / "overview.csv", index=False, encoding="utf-8-sig")
    (BASE_DIR / "data/processed/spot_inventory.json").write_text(
        json.dumps(inventory(), ensure_ascii=False, indent=2), encoding="utf-8")
    return overview


if __name__ == "__main__":
    print(json.dumps(export_summaries(), ensure_ascii=False, indent=2))
