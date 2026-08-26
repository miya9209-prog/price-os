import streamlit as st

from pricing_rules import PricingDefaults
from services.cafe24 import cafe24_status
from ui.calculator import render_calculator

st.set_page_config(
    page_title="MISHARP 가격책정 OS",
    page_icon="₩",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1280px;}
[data-testid="stSidebar"] {display:none;}
div[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.18); padding: 14px; border-radius: 12px;}
.misharp-red-metric {
  border: 1px solid rgba(128,128,128,.18);
  padding: 14px;
  border-radius: 12px;
  min-height: 106px;
  background: var(--background-color);
}
.misharp-red-metric-label {
  font-size: 0.86rem;
  margin-bottom: 10px;
}
.misharp-red-metric-value {
  color: #d71920;
  font-size: 2rem;
  line-height: 1.2;
  font-weight: 600;
  white-space: nowrap;
}
.misharp-red-metric-note {
  margin-top: 6px;
  font-size: 0.8rem;
  color: #d71920;
}
/* Reference values positioned exactly under the slider value coordinates. */
.misharp-slider-scale {
  position: relative;
  width: 100%;
  height: 0.95rem;
  box-sizing: border-box;
  margin: -1.55rem 0 0.42rem 0;
  color: rgba(49, 51, 63, 0.78);
  font-size: 0.74rem;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  pointer-events: none;
  overflow: visible;
}
.misharp-scale-label {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  text-align: center;
  white-space: nowrap;
}
@media (max-width: 768px) {
  .block-container {padding-left: .8rem; padding-right: .8rem; padding-top: .8rem;}
  div[data-testid="stHorizontalBlock"] {gap: .35rem;}
  .misharp-slider-scale {font-size: 0.62rem; margin-top: -1.45rem;}
}
</style>
""",
    unsafe_allow_html=True,
)

st.title("MISHARP 가격책정 OS")
st.caption("신상품 가격 · 마진 · 공헌이익 의사결정 시스템")

menu = st.radio(
    "메뉴",
    ["가격 계산", "상품별 수익성", "가격 AI", "데이터·설정"],
    horizontal=True,
    label_visibility="collapsed",
)

DEFAULTS = PricingDefaults()

if menu == "가격 계산":
    render_calculator(DEFAULTS)

elif menu == "상품별 수익성":
    st.subheader("상품별 수익성")
    st.info("V2에서 Cafe24 상품정보와 저장된 가격 시뮬레이션을 연결합니다.")
    st.markdown("예정 기능: 상품 검색 · 원가/판매가 · 공헌이익 등급 · 가격 위험 상품 · 일괄 비교")

elif menu == "가격 AI":
    st.subheader("가격 AI")
    st.info("V2/V3에서 경쟁사·네이버 유사상품 가격과 미샵 과거 판매 데이터를 연결합니다.")
    st.markdown(
        """
**목표 출력**

- 왜 이 가격을 추천하는가
- 경쟁사 대비 가격 위치
- 최대 할인 가능 범위
- 광고비가 몇 %까지 올라가도 손익을 지키는가
- 가격 인상/인하 시 예상 리스크
- 실행 후 3일/7일/14일 검증
        """
    )

else:
    st.subheader("데이터·설정")
    status = cafe24_status()
    st.write("**Cafe24 API**")
    st.warning(status["message"] if not status["connected"] else "연결됨")
    st.divider()
    st.write("**V1 기본 비용률**")
    st.json({
        "세금평균": f"{DEFAULTS.tax_rate}%",
        "수수료": f"{DEFAULTS.payment_fee_rate}%",
        "포장비": f"{DEFAULTS.packaging_rate}%",
        "광고비": f"{DEFAULTS.ad_rate}%",
        "상품단가X배수": f"{DEFAULTS.target_multiple}배",
    })

st.divider()
st.caption("MISHARP COMPANY INTERNAL USE ONLY · MISHARP COMPANY PARK HYUNG JOON")
