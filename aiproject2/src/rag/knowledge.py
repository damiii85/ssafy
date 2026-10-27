"""기존 CSV·지정 PDF를 RAG 문서로 구성하고 출처·지역을 보존한다."""
import hashlib
import json
from functools import lru_cache
from pathlib import Path

from pypdf import PdfReader

from src.rag.settings import BASE_DIR
from src.services.pdf_evidence import PDF_PATH, report_data, METRICS, UNITS
from src.services.pilot_report import load_spot_data, CATEGORY_FIELDS
from src.services.spot_catalog import load_spots, data_paths

MANIFEST = BASE_DIR / 'data/processed/rag_inventory.json'


@lru_cache(maxsize=64)
def _file_digest(path, size, modified):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def corpus_signature():
    paths = [PDF_PATH, PDF_PATH.with_name('active_report.source.json'), BASE_DIR/'config/daegu_spots.json']
    for spot in load_spots():
        paths.extend(data_paths(spot['id']))
    # ZIP extraction changes timestamps; content hashes remain portable.
    state = [(str(p.relative_to(BASE_DIR)), _file_digest(str(p), p.stat().st_size, p.stat().st_mtime_ns)) for p in paths if p.exists()]
    return hashlib.sha256(json.dumps(state, ensure_ascii=True).encode()).hexdigest()


def pdf_documents():
    """활성 PDF만 사용한다. 통계표는 지역별 행으로 분리해 타 지역 혼입을 막는다."""
    if not PDF_PATH.is_file():
        return []
    meta = json.loads(PDF_PATH.with_name('active_report.source.json').read_text(encoding='utf-8'))
    pages = PdfReader(PDF_PATH).pages
    digest = hashlib.sha256(PDF_PATH.read_bytes()).hexdigest()
    if meta.get('sha256') != digest:
        raise ValueError('활성 보고서 해시가 다릅니다. 보고서 메타데이터부터 확인해 주세요.')
    result = []
    for spot in load_spots():
        regions = [c['name'] for c in spot.get('components', [])] or [spot['name']]
        for region in regions:
            data = report_data(region)
            for kind, page, text in (
                ('pdf_chapter', data['page'], pages[data['page']-1].extract_text() or ''),
                ('pdf_statistics', 2, '\n'.join([f'{region} · PDF 지정 상권 경계 통계'] + [f'{m}: {data["metrics"][m]:,}{u}' for m,u in zip(METRICS,UNITS)])),
            ):
                result.append({'url':f'pdf:{digest}:{spot["id"]}:{region}:{kind}',
                    'title':f'{region} · {"지역 설명" if kind=="pdf_chapter" else "지역 통계"}',
                    'source':str(PDF_PATH.relative_to(BASE_DIR)).replace('\\','/'),
                    'source_type':kind, 'region_id':spot['id'], 'region_name':region, 'page':page,
                    'collected_at':meta.get('collected_at') or '사용자 제공 · 수집일 미기록',
                    'reference':json.dumps(meta['data_reference_period'], ensure_ascii=False),
                    'content_type':'pdf', 'text':text, 'usage_note':'사용자 제공 활성 문서 · 프로젝트 내부 분석; 재배포 조건 별도 확인',
                    'robots_note':'로컬 사용자 제공 파일 · 웹 요청 없음', 'corpus_hash':digest})
    return result


def store_documents():
    """RAG 1에 지역·공식 업종 메타데이터를 색인. 전체 개수는 항상 원본 CSV로 별도 계산."""
    result=[]
    for spot in load_spots():
        frame, meta=load_spot_data(spot['id'])
        base={'region_id':spot['id'], 'region_name':spot['name'], 'source':meta['source'],
              'source_type':'store_metadata', 'collected_at':meta['collected_at_utc'],
              'reference':','.join(meta.get('source_date_range',[meta['collected_at_utc'][:10]])),
              'content_type':'api_metadata', 'usage_note':'공공 상가정보 수집본 · docs/data_sources.md 참조',
              'robots_note':'기수집 공공 API CSV · 추가 호출 없음', 'page':0}
        for level,column in [('region',None),*CATEGORY_FIELDS.items()]:
            groups=[('',frame)] if column is None else frame.groupby(column,sort=True)
            for name,rows in groups:
                if column and not name:
                    continue
                text=f"선택 지역: {spot['name']}\n행정구역: 대구 {spot['district']}\n업종 수준: {level}\n업종: {name or '지역 전체'}\n수집본 등록 상가: {len(rows):,}곳\n수집 범위: {meta.get('note') or str(meta['radius_m'])+'m'}\n집계 주의: 벡터 검색의 반환 건수를 전체 상가 수로 사용하지 않습니다. 실제 질문의 반경은 원본 CSV로 다시 계산합니다."
                result.append(dict(base, url=f"metadata:{spot['id']}:{level}:{name}", title=f"{spot['name']} · {name or '지역 전체'} 메타데이터",
                                   category_level=level, category_name=str(name), text=text))
    return result


def inventory():
    import chromadb
    from src.rag.portable_db import chroma_path
    client=chromadb.PersistentClient(path=str(chroma_path()))
    return {collection.name:collection.count() for collection in client.list_collections()}
