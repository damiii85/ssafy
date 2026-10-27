"""보고서 개정에 따른 지역 설정 변경. 원본 세 구역은 통합 집계 입력으로 보존."""
import json
import hashlib
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
path = BASE / 'config/daegu_spots.json'
current = json.loads(path.read_text(encoding='utf-8'))
by_id = {spot['id']: spot for spot in current}
if 'daegu_downtown' in by_id:
    components = by_id['daegu_downtown']['components']
else:
    components = [by_id[key] for key in ('dongseongro', 'daegu_station', 'banwoldang')]
core = dict(id='daegu_downtown', name='대구 도심 통합상권', district='중구',
            latitude=35.87, longitude=128.595, radius_m=1000,
            anchor='도심 대표 기준점(동성로 기존 수집 중심)', components=components,
            scope_note='동성로·대구역·반월당 수집 반경의 합집합. 상가 ID 중복 제거.')
new = [core, by_id['suseongmot'], by_id['samdeok']]
for key, name, district, lat, lon in [('dongdaegu','동대구역','동구',35.879,128.628),
                                    ('chilgok3','칠곡3지구','북구',35.943,128.563)]:
    new.append(dict(id=key, name=name, district=district, latitude=lat, longitude=lon,
                    radius_m=1000, anchor=name+' 기존 파일럿 수집 중심',
                    anchor_source='기존 지역 설정(Git 6e40d88) 복원. 역/상권 경계의 정확한 중심이 아님.'))
path.write_text(json.dumps(new, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
report = BASE / 'data/reports/상권보고서.pdf'
if report.exists():
    from pypdf import PdfReader
    record = {'file': str(report.relative_to(BASE)).replace('\\', '/'),
              'title': '대구광역시 주요 상권 분석 보고서 개정판', 'source_type': 'user_provided',
              'active_chat_report': True, 'page_count': len(PdfReader(report).pages),
              'sha256': hashlib.sha256(report.read_bytes()).hexdigest(), 'published_at': None,
              'data_reference_period': {'stores_footfall_sales_residents': '2026-07', 'workers_income_spending': '2026-06'},
              'statistics_page': 2, 'definition_pages': [1, 10],
              'region_pages': {'동성로':[3], '대구역':[4], '반월당':[5], '수성못':[6], '삼덕동':[7], '동대구역':[8], '칠곡3지구':[9]},
              'downtown_policy': 'PDF 세 구역 통계 합산 금지. API 상가 ID 중복 제거 합집합과 별도.',
              'new_regions_boundary': '동대구역·칠곡3지구 PDF 상권 경계 미확정', 'indexed': False}
    (report.parent / 'active_report.source.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    manifest_path = report.parent / 'latest_report_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    manifest = [entry for entry in manifest if not entry.get('active_chat_report')]
    manifest.append(record)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
