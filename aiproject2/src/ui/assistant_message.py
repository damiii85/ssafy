"""구조화된 분석 결과를 표시한다. 서비스 응답과 집계 값은 수정하지 않는다."""
import json
import math
from numbers import Integral, Real
from urllib.parse import urlparse
from pathlib import PureWindowsPath

import altair as alt
import pandas as pd
import streamlit as st

from src.services.pdf_evidence import PDF_PATH, METRICS
from src.ui.analytics import bar_chart


_COPY_DEFINITION = dict(
    name='spotcheck_answer_copy',
    html='<div class="footer"><time></time><button type="button" aria-label="답변 복사">⧉ 답변 복사</button><span role="status" aria-live="polite"></span></div>',
    css='''.footer{display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-family:var(--st-font,sans-serif);font-size:11px;color:#8191aa}time{margin-right:auto}button{border:1px solid #dde8f7;background:white;color:#2772c9;border-radius:9px;padding:6px 10px;cursor:pointer;font:inherit}button:focus-visible{outline:2px solid #1975ff;outline-offset:2px}''',
    js='''export default function({data,parentElement}) {
      const button=parentElement.querySelector('button');
      const status=parentElement.querySelector('[role="status"]');
      parentElement.querySelector('time').textContent=data.time || '';
      button.onclick=async()=>{
        try {
          if(navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(data.text);
          else {
            const input=document.createElement('textarea');input.value=data.text;
            input.style.position='fixed';input.style.opacity='0';document.body.append(input);
            try {input.select();if(!document.execCommand('copy'))throw new Error('copy');}
            finally {input.remove();}
          }
          status.textContent='복사했습니다';
        } catch(error) {status.textContent='복사하지 못했습니다. 상세 내용을 선택해 복사해 주세요.';}
      };
      return ()=>{button.onclick=null;};
    }''',
)


def summary_values(visual):
    """미확인/잘못된 값을 0으로 꾸미지 않고 비중의 0 나누기만 방지한다."""
    total, selected = visual.get('total_stores'), visual.get('competitor_count')
    if any(not isinstance(v, Integral) or isinstance(v, bool) for v in (total, selected)):
        return None
    if not 0 <= selected <= total:
        return None
    return {'total': int(total), 'selected': int(selected), 'other': int(total-selected),
            'share': selected / total if total else None}


def source_dates(visual):
    dates = visual.get('source_dates') or ([str(visual['collected_at'])[:10]] if visual.get('collected_at') else [])
    if isinstance(dates, str):
        dates = [dates]
    return ', '.join(map(str, dates)) if dates else '기준일 미확인'


def _pdf_metadata():
    try:
        data = json.loads(PDF_PATH.with_name('active_report.source.json').read_text(encoding='utf-8'))
        return data if isinstance(data, dict) and str(data.get('file', '')).endswith('/' + PDF_PATH.name) else {}
    except (OSError, ValueError, TypeError):
        return {}


def analysis_summary(visual, key):
    values = summary_values(visual)
    with st.container(border=False, key='answer-summary-' + key):
        st.markdown(f'**:material/location_on: {visual.get("spot", "선택 지역")} 상권 요약**')
        st.caption(visual.get('scope_description', '집계 범위 미확인'))
        with st.container(key='answer-kpis-' + key):
            a, b, c = st.columns(3)
            a.metric(':material/storefront: API 전체 상가', f"{values['total']:,}곳" if values else '데이터 없음')
            b.metric(':material/category: 선택 업종', f"{values['selected']:,}곳" if values else '데이터 없음')
            c.metric(':material/percent: 전체 대비 비중', f"{values['share']:.1%}" if values and values['share'] is not None else '데이터 없음')
        with st.expander('업종 비중 보기', expanded=False):
            st.markdown('**업종 비중**')
            if not values or not values['total']:
                st.caption('데이터 없음 · 비중을 계산할 전체 상가 데이터가 없습니다.')
            else:
                with st.container(key='answer-donut-' + key):
                    chart_col, legend_col = st.columns([1, 1.15], vertical_alignment='center')
                    with chart_col:
                        frame = pd.DataFrame([{'구분':'선택 업종','점포 수':values['selected']},
                                              {'구분':'그 외 업종','점포 수':values['other']}])
                        arc = alt.Chart(frame).mark_arc(innerRadius=48, outerRadius=69, cornerRadius=3).encode(
                            theta='점포 수:Q', color=alt.Color('구분:N', legend=None,
                            scale=alt.Scale(domain=['선택 업종','그 외 업종'],range=['#2276ff','#e6eefb'])),
                            tooltip=['구분:N',alt.Tooltip('점포 수:Q',format=',')])
                        center = alt.Chart(pd.DataFrame([{'label':f"{values['share']:.1%}"}])).mark_text(
                            fontSize=23,fontWeight='bold',color='#102144').encode(text='label:N')
                        chart = (arc+center).properties(height=155,
                            description=f"선택 업종 {values['selected']:,}곳, {values['share']:.1%}. 그 외 {values['other']:,}곳.").configure_view(strokeWidth=0)
                        st.altair_chart(chart, width='stretch', key='donut-' + key)
                    with legend_col:
                        st.html(f'<div class="answer-legend"><div><i></i><span>선택 업종<strong>{values["selected"]:,}곳 <small>({values["share"]:.1%})</small></strong></span></div><div><i class="other"></i><span>그 외 업종<strong>{values["other"]:,}곳 <small>({1-values["share"]:.1%})</small></strong></span></div></div>')

def _filename(value):
    return PureWindowsPath(str(value)).name


def _safe_url(value):
    parsed = urlparse(str(value))
    return parsed.scheme in ('http', 'https') and bool(parsed.netloc)


def _source_label(citation):
    source = str(citation.get('source') or '')
    name = _filename(source)
    if name.lower().endswith('.pdf'):
        return name[:-4] + ' · PDF'
    if _safe_url(source):
        parsed = urlparse(source)
        if parsed.hostname == 'apis.data.go.kr' and '/B553077/' in parsed.path:
            return '소상공인시장진흥공단 · 상가정보'
        return parsed.hostname + ' · ' + str(citation.get('title') or '참고 자료')
    return str(citation.get('title') or '출처 미확인')


def _reference_text(reference):
    """원시 메타데이터의 항목명만 바꾸고 실제 값은 보존한다."""
    if isinstance(reference, str):
        try:
            parsed = json.loads(reference)
        except (ValueError, TypeError):
            return reference
    else:
        parsed = reference
    labels = {'stores_footfall_sales_residents': '업소·유동인구·매출·주거인구',
              'workers_income_spending': '직장인구·소득·소비'}
    if isinstance(parsed, dict):
        return ' / '.join(f'{labels.get(k, "자료 기준")}: {_reference_text(v)}' for k, v in parsed.items())
    if isinstance(parsed, list):
        return ', '.join(_reference_text(v) for v in parsed)
    return str(parsed) if parsed is not None else '기준일 미확인'


def source_reference(visual, background, key, citations=()):
    with st.container(key='answer-sources-' + key):
        st.markdown('**:material/description: 참고 자료**')
        grouped = {}
        for citation in citations:
            grouped.setdefault(_source_label(citation), []).append(f'[근거 {citation["number"]}]')
        for label, refs in grouped.items():
            st.caption(label + '  ' + ' '.join(dict.fromkeys(refs)))
        if not grouped:
            if visual.get('source'):
                st.caption(_source_label({'source': visual['source']}))
            else:
                st.caption('답변에 연결된 문서 근거가 없습니다.')


def evidence_details(message, visual, key):
    citations = message.get('citations') or []
    with st.expander('상세 근거 및 분석 기준', expanded=False):
        for citation in citations:
            st.markdown(f'**[근거 {citation["number"]}] {citation.get("title", "자료")}**')
            source = str(citation.get('source') or '출처 미확인')
            st.caption('원문: ' + (_filename(source) if not _safe_url(source) else source))
            if _safe_url(source):
                st.link_button('원문 사이트', source)
            if citation.get('page'):
                st.caption(f'PDF 페이지: {citation["page"]}쪽')
            st.caption('데이터 기준: ' + _reference_text(citation.get('reference')))
            if citation.get('scope'):
                st.caption('집계 범위: ' + str(citation['scope']))
            if citation.get('document_id'):
                st.caption('문서 식별자: ' + str(citation['document_id']))
        if visual.get('type') == 'overview':
            st.caption('API 원본 수집일: ' + source_dates(visual))
            st.caption('집계 범위: ' + visual.get('scope_description', '집계 범위 미확인'))
            st.caption('실제 거리 필터·상가 ID 중복 제거 집계입니다. 수집 시점의 등록 정보이며 현재 영업 여부는 별도 확인이 필요합니다.')
        pdf_used = any(_filename(c.get('source', '')) == PDF_PATH.name for c in citations)
        pdf_used = pdf_used or (visual.get('type') == 'pdf_metrics' and _filename(visual.get('source', '')) == PDF_PATH.name)
        if pdf_used:
            periods = _pdf_metadata().get('data_reference_period')
            if periods:
                st.caption('보고서 기준연월: ' + _reference_text(periods))
            if visual.get('reference'):
                st.caption('참고 페이지: ' + _reference_text(visual['reference']))
            st.caption('PDF 지정 상권 경계의 과거 통계로, API 수집 범위·시점과 다릅니다. 주소 반경의 유동인구나 매출로 환산할 수 없습니다.')
            if PDF_PATH.is_file():
                st.download_button('PDF 다운로드', PDF_PATH.read_bytes(), file_name=PDF_PATH.name,
                                   mime='application/pdf', icon=':material/download:', key='answer-pdf-' + key, on_click='ignore')
        if not citations:
            st.caption('연결된 문서 근거가 없습니다. 확인할 수 없는 수치는 추정하지 않습니다.')
        if message.get('rag_status'):
            st.markdown('**자료 확인 안내**')
            for status in message['rag_status']:
                st.caption(status)
        st.markdown('**전체 답변**')
        st.markdown(str(message.get('content') or ''))


def analysis_insight(visual, background, key, citations=()):
    rows = [row for row in (visual.get('rows') or []) if isinstance(row, dict)
            and all(row.get(field) is not None for field in ('지역', '지표', '단위'))
            and isinstance(row.get('값'), Real) and not isinstance(row.get('값'), bool)
            and math.isfinite(row['값'])]
    with st.container(key='answer-insight-' + key):
        metrics = list(dict.fromkeys(row['지표'] for row in rows))
        st.markdown('**' + (' · '.join(metrics) + ' 분석' if metrics else '보고서 분석') + '**')
        if not rows:
            st.caption('데이터 없음 · 보고서 지표가 완전하지 않습니다.')
        for metric in metrics:
            selected = [r for r in rows if r['지표'] == metric]
            with st.container(key='answer-kpis-' + key + '-' + str(metrics.index(metric))):
                if len(selected) == 1:
                    row = selected[0]
                    label = '일평균 유동인구' if metric == '유동인구' else metric
                    st.metric(row['지역'] + ' · ' + label, f"{row['값']:,}{row['단위']}")
                else:
                    bar_chart(selected, '지역', '값', key + '-' + metric, 140)
        if len(rows) != len(visual.get('rows') or []):
            st.caption('정보가 완전한 지표만 표시했습니다.')


def _analysis_text(content, visual):
    """고정 서비스 응답의 설명을 발췌한다. 전체 원문은 상세 영역에 유지한다."""
    paragraphs = content.split('\n\n')
    if visual.get('type') == 'overview':
        guide = []
        regional = []
        in_report = False
        for i, paragraph in enumerate(paragraphs):
            if paragraph == '**어떤 업종인가요?**' and i + 1 < len(paragraphs):
                guide.append(paragraphs[i + 1])
            if '· 보고서에서 확인한 내용**' in paragraph:
                in_report = True
            if (in_report and '[근거 ' in paragraph and not paragraph.startswith(('**', '출처:', '> '))
                    and not any(paragraph.startswith(m + ':') for m in METRICS)):
                regional.append(paragraph)
        quotes = [p for p in paragraphs if p.startswith('> ')]
        return '\n\n'.join(dict.fromkeys(guide + regional[:2] + quotes))
    if visual.get('type') == 'pdf_metrics':
        return '\n\n'.join(p for p in paragraphs if p and not (
            p.startswith(('**', '출처:', '보고서 기준연월:'))
            or any(p.startswith(m + ':') for m in METRICS)))
    return content


def assistant_message(message, key):
    visual = message.get('visual') or {}
    content = str(message.get('content') or '')
    with st.container(border=False, key='answer-card-' + key):
        structured = visual.get('type') in ('overview', 'pdf_metrics')
        if structured:
            st.markdown('선택한 범위의 업종 현황을 정리했습니다.' if visual['type'] == 'overview'
                        else '보고서에서 확인한 내용을 정리했습니다.')
            if visual['type'] == 'overview':
                analysis_summary(visual, key)
            else:
                analysis_insight(visual, None, key, message.get('citations', []))
        explanation = _analysis_text(content, visual)
        if explanation:
            st.markdown(explanation)
        if structured:
            st.caption('수집·보고서 기준 자료입니다. 현재 현황과 분석 범위는 상세 근거를 확인해 주세요.')
        source_reference(visual, None, key, message.get('citations', []))
        evidence_details(message, visual, key)
    # 1.62의 컴포넌트 레지스트리는 세션/테스트별로 새로 구성된다.
    copy_component = st.components.v2.component(**_COPY_DEFINITION)
    copy_component(data={'text':content, 'time':message.get('time', '')}, key='answer-copy-' + key, height='content')


def apply_answer_styles():
    st.html('''<style>
    .st-key-chat-feed [data-testid="stChatMessage"]:has([class*="st-key-answer-card-"]){width:94%;max-width:100%}
    div[class*="st-key-answer-card-"]{min-width:0;width:100%;padding:0!important;gap:16px;border:0!important;background:transparent;container-type:inline-size}
    div[class*="st-key-answer-summary-"],div[class*="st-key-answer-insight-"],div[class*="st-key-answer-sources-"]{padding:0!important;gap:12px;border:0!important;background:transparent;min-width:0;max-width:100%}
    div[class*="st-key-answer-summary-"] [data-testid="stCaptionContainer"] p,div[class*="st-key-answer-sources-"] [data-testid="stCaptionContainer"] p{font-size:11px!important;line-height:1.6!important;color:#8191aa}
    .st-key-chat-feed div[class*="st-key-answer-sources-"] [data-testid="stCaptionContainer"] p{font-size:12px!important;color:#64748b!important}
    div[class*="st-key-answer-kpis-"] [data-testid="stMetric"]{padding:10px;background:#f2f7ff;border:0;border-radius:12px;min-width:0}
    div[class*="st-key-answer-kpis-"] [data-testid="stMetricLabel"] p{font-size:12px!important}
    div[class*="st-key-answer-kpis-"] [data-testid="stMetricValue"]{font-size:24px!important;font-weight:800;color:#102144}
    .st-key-chat-feed div[class*="st-key-answer-kpis-"] [data-testid="stMetricValue"] p{font-size:24px!important;line-height:1.3!important;font-weight:800;color:#102144}
    div[class*="st-key-answer-kpis-"] [data-testid="stIconMaterial"]{font-size:16px;color:#2276ff}
    div[class*="st-key-answer-insight-"] [data-testid="stMarkdownContainer"] strong{color:#2276ff}
    div[class*="st-key-answer-insight-"]>[data-testid="stElementContainer"]:first-child strong{color:#102144}
    .answer-legend>div{display:flex;align-items:flex-start;gap:8px;margin:14px 0;font-size:12px;color:#7687a2}.answer-legend i{width:9px;height:9px;border-radius:50%;background:#2276ff;margin-top:5px;flex-shrink:0}.answer-legend i.other{background:#e6eefb}.answer-legend strong{display:block;font-size:16px;color:#102144;margin-top:4px}.answer-legend small{font-size:12px;font-weight:400}
    div[class*="st-key-answer-card-"] [data-testid="stExpander"]{border-color:#e2ebf8;border-radius:10px}
    div[class*="st-key-answer-card-"] iframe,div[class*="st-key-answer-card-"] canvas,div[class*="st-key-answer-card-"] svg{max-width:100%}
    @container(max-width:420px){
      div[class*="st-key-answer-kpis-"] [data-testid="stHorizontalBlock"]{flex-wrap:wrap!important;gap:8px}
      div[class*="st-key-answer-kpis-"] [data-testid="stColumn"]{flex:1 1 125px!important;min-width:0!important}
      div[class*="st-key-answer-donut-"] [data-testid="stHorizontalBlock"]{flex-wrap:wrap!important;gap:0}
      div[class*="st-key-answer-donut-"] [data-testid="stColumn"]{flex:1 1 100%!important;min-width:0!important}
      .answer-legend{display:flex;justify-content:space-around;gap:12px}
    }
    </style>''')
