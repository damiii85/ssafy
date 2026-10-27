"""지역 단위 수치 카드와 실제 데이터 기반 차트."""
import altair as alt
import pandas as pd
import streamlit as st

from src.services.region_analytics import distribution_rows


def bar_chart(rows, category, value, key, height=200):
    if not rows:
        st.caption('표시할 데이터가 없습니다.')
        return
    data = pd.DataFrame(rows)
    chart = alt.Chart(data).mark_bar(cornerRadiusEnd=5, color='#3984ff', height=16).encode(
        x=alt.X(f'{value}:Q', title=value, axis=alt.Axis(format=',d', tickMinStep=1)),
        y=alt.Y(f'{category}:N', sort='-x', title=None, axis=alt.Axis(labelLimit=140)),
        tooltip=[alt.Tooltip(f'{category}:N'), alt.Tooltip(f'{value}:Q', format=',')],
    ).properties(height=height).configure_view(strokeWidth=0)
    # 요구서의 Streamlit 1.62에는 alt 인자가 없다. Vega 설명으로 접근성을 유지한다.
    chart = chart.properties(description=f'{category}별 {value}. 마우스를 올리면 실제 수치를 확인할 수 있습니다.')
    st.altair_chart(chart, width='stretch', key=key)


def render_visual(visual, key):
    if not visual:
        return
    if visual['type'] == 'overview':
        with st.container(border=True, key='summary-' + key):
            st.markdown('**한눈에 보는 업종 현황**')
            st.caption('집계 기준: ' + visual.get('scope_description', visual['spot'] + ' 수집 범위'))
            total, count = visual['total_stores'], visual['competitor_count']
            a, b, c = st.columns(3)
            a.metric('API 전체 상가', f'{total:,}곳')
            b.metric('선택 업종', f'{count:,}곳')
            c.metric('전체 대비 비중', f'{count / total:.1%}' if total else '집계 없음')
            donut = alt.Chart(pd.DataFrame([
                {'구분': '선택 업종', '점포 수': count}, {'구분': '그 외 업종', '점포 수': total - count}
            ])).mark_arc(innerRadius=48, outerRadius=72, cornerRadius=4).encode(
                theta=alt.Theta('점포 수:Q'),
                color=alt.Color('구분:N', scale=alt.Scale(domain=['선택 업종', '그 외 업종'], range=['#2276ff', '#e6eefb']), legend=alt.Legend(orient='bottom', title=None)),
                tooltip=['구분:N', alt.Tooltip('점포 수:Q', format=',')],
            ).properties(height=155).configure_view(strokeWidth=0)
            donut = donut.properties(description='API 수집본 내 선택 업종과 나머지 업종의 점포 비중')
            st.altair_chart(donut, width='stretch', key='donut-' + key)
            st.caption(f"출처: 상가정보 API · {', '.join(visual.get('source_dates', [visual['collected_at'][:10]]))} 수집. 위 기준의 실제 거리 필터·중복 제거 집계이며 현재 영업 여부와 PDF 경계는 별도입니다.")
    elif visual['type'] == 'pdf_metrics':
        with st.container(border=True, key='pdf-chart-' + key):
            st.markdown('**보고서 수치 한눈에 보기**')
            # 서로 다른 단위·지표를 한 축에 비교하지 않는다.
            for metric in dict.fromkeys(row['지표'] for row in visual['rows']):
                rows = [row for row in visual['rows'] if row['지표'] == metric]
                if len(rows) == 1:
                    row = rows[0]
                    st.metric(f"{row['지역']} · {metric}", f"{row['값']:,}{row['단위']}")
                else:
                    st.caption(f"{metric} ({rows[0]['단위']})")
                    bar_chart(rows, '지역', '값', f'{key}-{metric}', 140)
            st.caption(f"출처: {visual['source']} · {visual['reference']}. PDF 지정 경계의 과거 통계이며 반경 집계와 다릅니다.")
