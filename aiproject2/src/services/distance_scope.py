"""질문의 반경을 실제 좌표 거리 필터에 적용한다. 특정 점포 추천 없음."""
import math
import re

from src.services.location_analyzer import calculate_distance


def requested_radius(question):
    matches = re.findall(r'(?<![\d.])(-?\d+(?:,\d{3})*(?:\.\d+)?)\s*(km|킬로미터|킬로|미터|메터|m(?![a-z]))', question, re.I)
    values = set()
    for number, unit in matches:
        value = float(number.replace(',', '')) * (1000 if unit.lower() in ('km', '킬로미터', '킬로') else 1)
        if not math.isfinite(value) or value <= 0:
            raise ValueError('분석 반경은 0보다 큰 거리로 입력해 주세요.')
        values.add(round(value, 6))
    if len(values) > 1:
        raise ValueError('한 질문에는 한 개의 반경을 지정해 주세요. 예: 100m 이내 카페 현황.')
    return next(iter(values)) if values else None


def scoped_stores(spot_id, stores, metadata, question, state, location=None):
    explicit = requested_radius(question)
    previous = state.get('distance_scope', {})
    reset = any(word in question for word in ('전체 범위', '전체범위', '지역 전체', '통합상권 전체'))
    radius = explicit if explicit is not None else (previous.get('radius_m') if previous.get('spot_id') == spot_id and not reset else None)
    if radius is None:
        meta = dict(metadata)
        meta['scope_kind'] = 'union' if metadata.get('coverage_type') == 'union_of_circles' else 'region'
        meta['scope_center'] = metadata.get('spot_name', '') + ' 기준점'
        meta['scope_description'] = (metadata.get('note', '').rstrip('.') if meta['scope_kind'] == 'union' else
                                     f"{meta['scope_center']}의 직선 반경 {metadata['radius_m']:,}m")
        if reset:
            state.pop('distance_scope', None)
        return stores, meta
    if any(term in question.replace(' ', '') for term in ('내위치', '내주변', '현재위치')) and not location:
        raise ValueError('현재 위치를 전달받지 않아 내 위치 기준 거리를 계산할 수 없습니다. 지역 기준점인지, 동성로·대구역·반월당 중 어느 기준인지 알려주세요.')
    latitude, longitude = metadata['center_lat'], metadata['center_lon']
    label = metadata.get('anchor', metadata.get('spot_name', '선택 지역') + ' 기준점').split(' (API pilot', 1)[0]
    if location:
        latitude, longitude = location['latitude'], location['longitude']
        label = location.get('address', '사용자가 지정한 기준점')
    if not all(math.isfinite(float(v)) for v in (latitude, longitude)) or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError('거리 계산 기준 좌표가 유효하지 않습니다.')
    coverages = metadata.get('components') or [metadata]
    complete = any(calculate_distance(latitude, longitude, c['center_lat'], c['center_lon']) + radius <= c['radius_m'] + 1e-6 for c in coverages)
    if not complete:
        raise ValueError(f"요청한 {radius:g}m 원 전체가 현재 API 수집 범위 안에 있지 않아 정확한 전체 점포 수를 알 수 없습니다. 더 작은 반경이나 다른 기준점을 지정해 주세요.")
    distances = [calculate_distance(latitude, longitude, row.lat, row.lon) for row in stores.itertuples()]
    selected = stores.loc[[distance <= radius + 1e-6 for distance in distances]].copy()
    meta = dict(metadata, radius_m=radius, scope_kind='radius', scope_center=label,
                scope_description=f'{label} 기준 직선 반경 {radius:g}m (현재 사용자 위치 기준 아님)' if not location else f'{label} 기준 직선 반경 {radius:g}m', coverage_complete=True,
                available_radius_m=metadata['radius_m'])
    meta['scope_latitude'], meta['scope_longitude'] = latitude, longitude
    if location:
        meta['scope_coordinate_source'] = location.get('source', '사용자 제공 좌표')
        meta['scope_description'] += f" · 위치 출처: {meta['scope_coordinate_source']}"
    state['distance_scope'] = {'spot_id': spot_id, 'radius_m': radius}
    return selected, meta
