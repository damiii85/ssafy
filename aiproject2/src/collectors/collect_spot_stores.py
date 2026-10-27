"""스팟별 상가 수집. 기존 동성로 CSV 및 벡터 DB를 보존한다."""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd
import requests
from dotenv import load_dotenv

from src.collectors.store_api import unpack, URL
from src.services.spot_catalog import get_spot, load_spots, data_paths, inventory


def collect_spot(spot_id, refresh=False, session=None):
    spot = get_spot(spot_id)
    if spot.get('components'):
        frames, sources = [], []
        for component in spot['components']:
            meta = collect_spot(component['id'], refresh, session)
            csv_path, _ = data_paths(component['id'])
            frames.append(pd.read_csv(csv_path, dtype=str).fillna('').assign(_collected=meta['collected_at_utc']))
            sources.append(meta)
        combined = pd.concat(frames, ignore_index=True).sort_values('_collected', ascending=False, kind='stable')
        combined = combined.drop_duplicates('bizesId').drop(columns='_collected')
        directory = BASE_DIR / 'data/raw/spots' / spot_id
        directory.mkdir(parents=True, exist_ok=True)
        metadata = {'spot_id': spot_id, 'spot_name': spot['name'], 'source': URL,
                    'collected_at_utc': max(s['collected_at_utc'] for s in sources),
                    'source_date_range': sorted({s['collected_at_utc'][:10] for s in sources}),
                    'assembled_at_utc': datetime.now(timezone.utc).isoformat(),
                    'center_lat': spot['latitude'], 'center_lon': spot['longitude'],
                    'radius_m': spot['radius_m'], 'count': len(combined), 'api_total': None,
                    'coverage_type': 'union_of_circles', 'components': sources,
                    'input_rows': sum(s['count'] for s in sources),
                    'duplicates_removed': sum(s['count'] for s in sources)-len(combined),
                    'anchor': spot['anchor'], 'note': spot['scope_note']}
        combined.to_csv(directory / 'stores.csv', index=False, encoding='utf-8-sig')
        (directory / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
        return metadata
    if spot["latitude"] is None or spot["longitude"] is None:
        raise ValueError("이 지역은 PDF 자료만 있습니다. 검증된 API 수집 중심 좌표가 필요합니다.")
    existing, meta = data_paths(spot_id)
    if existing.exists() and meta.exists() and not refresh:
        return json.loads(meta.read_text(encoding="utf-8"))
    load_dotenv(BASE_DIR / ".env")
    key = os.getenv("PUBLIC_DATA_API_KEY", "").strip()
    if not key:
        raise ValueError("PUBLIC_DATA_API_KEY가 필요합니다.")
    http = session or requests
    rows = []
    total_count = None
    for page in range(1, 101):
        try:
            response = http.get(URL, params={
                "serviceKey": unquote(key), "radius": spot["radius_m"],
                "cx": spot["longitude"], "cy": spot["latitude"],
                "pageNo": page, "numOfRows": 1000, "type": "json",
            }, timeout=(10, 40))
            response.raise_for_status()
            items, total = unpack(response.json())
        except (requests.RequestException, ValueError, RuntimeError):
            raise ValueError(f"{spot['name']} {page}페이지 조회 실패. 키·승인·네트워크를 확인해 주세요.") from None
        if total_count is not None and total_count != total:
            raise ValueError("수집 중 총 건수가 바뀌었습니다. 다시 실행해 주세요.")
        total_count = total
        rows.extend(items)
        print(f"{spot['name']} {page}페이지: 누적 {len(rows)}/{total}")
        if len(rows) >= total:
            break
        if not items:
            raise ValueError("미완료 응답입니다. 기존 파일을 보존합니다.")
        time.sleep(0.2)
    else:
        raise ValueError("페이지 제한으로 수집 미완료. 기존 파일을 보존합니다.")
    if not rows:
        raise ValueError("상가 조회 결과가 없습니다. 기존 파일을 보존합니다.")
    df = pd.DataFrame(rows)
    required = {"bizesId", "bizesNm", "indsLclsNm", "indsMclsNm", "indsSclsNm", "lat", "lon", "rdnmAdr"}
    if not required <= set(df.columns):
        raise ValueError("필수 상가 컬럼이 누락됐습니다.")
    df = df.dropna(subset=["bizesId"]).drop_duplicates("bizesId")
    directory = BASE_DIR / "data/raw/spots" / spot_id
    directory.mkdir(parents=True, exist_ok=True)
    metadata = {"spot_id": spot_id, "spot_name": spot["name"], "source": URL,
                "collected_at_utc": datetime.now(timezone.utc).isoformat(),
                "center_lon": spot["longitude"], "center_lat": spot["latitude"],
                "radius_m": spot["radius_m"], "api_total": total_count,
                "anchor": spot["anchor"], "anchor_source": spot.get("anchor_source", "config/daegu_spots.json"),
                "anchor_stop_id": spot.get("anchor_stop_id", ""),
                "anchor_reference_date": spot.get("anchor_reference_date", ""),
                "count": len(df), "note": "파일럿 원형 수집 범위. 공식 상권 경계가 아님"}
    df.to_csv(directory / "stores.csv", index=False, encoding="utf-8-sig")
    (directory / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def main():
    parser = argparse.ArgumentParser(description="대구 파일럿 스팟별 상가 수집")
    parser.add_argument("--spot", choices=[s["id"] for s in load_spots()] + ["all"], default="all")
    parser.add_argument("--refresh", action="store_true", help="기존 수집본도 갱신. 원본 동성로 파일은 보존")
    args = parser.parse_args()
    failed = False
    for spot in load_spots():
        if args.spot != "all" and args.spot != spot["id"]:
            continue
        try:
            meta = collect_spot(spot["id"], args.refresh)
            print(f"완료: {spot['name']} {meta['count']}건")
        except ValueError as error:
            print(f"오류: {error}", file=sys.stderr)
            failed = True
    output = BASE_DIR / "data/processed/spot_inventory.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inventory(), ensure_ascii=False, indent=2), encoding="utf-8")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
