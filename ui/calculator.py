import pandas as pd
import streamlit as st

from pricing_engine import PricingInput, calculate_pricing, build_why_diagnosis
from ui.components import won, pct, grade_badge


def render_calculator(defaults):
    st.subheader("신상품 가격 계산")
    st.caption("원가를 입력하면 정상판매가, 실결제가, 공헌이익, 손익 방어선을 계산합니다.")

    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            product_cost = st.number_input("상품원가", min_value=0, value=18000, step=500, format="%d")
            cost_basis = st.radio("상품원가 부가세 기준", ["부가세 포함", "부가세 별도"], horizontal=True)
            target_multiple = st.slider("목표 원가배수", 1.5, 5.0, float(defaults.target_multiple), 0.1)
            rounding = st.selectbox("판매가 끝자리", ["800원 끝", "900원 끝", "100원 단위"])
        with c2:
            ad_rate = st.slider("광고비율", 8, 15, int(defaults.ad_rate), 1)
            coupon_rate = st.slider("할인·쿠폰율", 0, 50, int(defaults.coupon_rate), 1)
            expected_qty = st.number_input("예상 판매수량", min_value=1, value=int(defaults.expected_qty), step=10)
            competitor = st.number_input("경쟁사 평균가격 (선택)", min_value=0, value=0, step=1000, format="%d")

    with st.expander("고급 비용 설정"):
        c1, c2, c3 = st.columns(3)
        tax_rate = c1.number_input("세금평균 (%)", min_value=0.0, max_value=20.0, value=float(defaults.tax_rate), step=0.1)
        payment_fee = c2.number_input("수수료 (%)", min_value=0.0, max_value=20.0, value=float(defaults.payment_fee_rate), step=0.1)
        packaging = c3.number_input("포장비 (%)", min_value=0.0, max_value=20.0, value=float(defaults.packaging_rate), step=0.1)
        st.caption("V1 기본값은 개발계획서의 세금평균 4%, 수수료 3.5%, 포장비 1%를 사용합니다.")

    base_inp = PricingInput(
        product_cost=float(product_cost),
        cost_vat_included=(cost_basis == "부가세 포함"),
        target_multiple=float(target_multiple),
        tax_rate=float(tax_rate),
        payment_fee_rate=float(payment_fee),
        packaging_rate=float(packaging),
        ad_rate=float(ad_rate),
        coupon_rate=float(coupon_rate),
        expected_qty=int(expected_qty),
        competitor_avg_price=float(competitor) if competitor else None,
        price_rounding=rounding,
    )
    provisional = calculate_pricing(base_inp)

    st.markdown("#### 판매가 확정")
    use_manual = st.toggle("추천 정상판매가 대신 직접 판매가 입력")
    manual = None
    if use_manual:
        manual = st.number_input("적용 정상판매가", min_value=0, value=int(provisional.list_price), step=100)
        base_inp.manual_list_price = float(manual)

    result = calculate_pricing(base_inp)

    st.divider()
    st.subheader("가격·수익성 결과")
    a, b, c, d = st.columns(4)
    a.metric("추천/적용 정상판매가", won(result.list_price))
    b.metric("쿠폰 적용 실결제가", won(result.paid_price), delta=f"-{won(result.discount_amount)}")
    c.metric("1장당 공헌이익", won(result.contribution_profit))
    d.metric("공헌이익률", pct(result.contribution_margin_rate))

    a, b, c = st.columns(3)
    a.metric(f"{expected_qty}장 총공헌이익", won(result.total_contribution_profit))
    b.metric("손익분기 광고비율", pct(result.max_ad_rate_before_loss))
    c.metric("손익분기 최대 쿠폰율", pct(result.max_coupon_rate_before_loss))

    with st.container(border=True):
        grade_badge(result.grade, result.grade_label)
        if result.competitor_gap_rate is not None:
            st.write(
                f"경쟁사 평균 {won(base_inp.competitor_avg_price)} 대비 "
                f"{won(abs(result.competitor_gap_amount))} "
                f"({'높음' if result.competitor_gap_amount > 0 else '낮음' if result.competitor_gap_amount < 0 else '동일'})"
            )

    st.subheader("비용 구조")
    cost_rows = [
        ["실결제가", result.paid_price],
        ["상품 현금원가", -result.product_cash_cost],
        ["납부 추정부가세", -result.vat_payable],
        [f"세금평균 {tax_rate:.1f}%", -result.tax_cost],
        [f"수수료 {payment_fee:.1f}%", -result.payment_fee_cost],
        [f"포장비 {packaging:.1f}%", -result.packaging_cost],
        [f"광고비 {ad_rate:.0f}%", -result.ad_cost],
        ["공헌이익", result.contribution_profit],
    ]
    df = pd.DataFrame(cost_rows, columns=["항목", "1장 기준 금액"])
    df["1장 기준 금액"] = df["1장 기준 금액"].map(lambda x: f"{x:,.0f}원")
    st.dataframe(df, hide_index=True, use_container_width=True)

    st.subheader("WHY 진단")
    for item in build_why_diagnosis(base_inp, result):
        with st.container(border=True):
            st.markdown(f"**[{item['level']}] {item['title']}**")
            st.write(item["reason"])
            st.caption(f"추천 실행: {item['action']}")

    st.subheader("가격 시뮬레이션")
    rows = []
    for coupon in range(0, 31, 5):
        for ad in range(8, 16):
            sim = PricingInput(**{**base_inp.__dict__, "coupon_rate": float(coupon), "ad_rate": float(ad)})
            r = calculate_pricing(sim)
            rows.append({
                "쿠폰율": f"{coupon}%",
                "광고비율": f"{ad}%",
                "실결제가": int(r.paid_price),
                "1장 공헌이익": int(r.contribution_profit),
                "공헌이익률": round(r.contribution_margin_rate, 1),
                "등급": r.grade,
            })
    sim_df = pd.DataFrame(rows)
    st.dataframe(sim_df, hide_index=True, use_container_width=True, height=360)

    with st.expander("V1 계산 기준 확인"):
        st.markdown(
            """
- 소비자 판매가는 **부가세 포함 가격**으로 계산합니다.
- 원가가 부가세 포함이면 매입부가세를 원가에서 분리하여 매출부가세와 상계합니다.
- 원가가 부가세 별도이면 원가에 10% 매입부가세가 추가되는 것으로 계산합니다.
- 할인·쿠폰은 정상판매가에서 차감하여 **실결제가**를 만든 뒤, 실결제가에 변동비를 적용합니다.
- 세금평균·수수료·포장비·광고비는 V1에서 모두 실결제가 대비 비율로 계산합니다.
- 실제 회계·정산 기준과 다르면 `pricing_engine.py`의 계산 규칙을 회사 기준에 맞게 수정해야 합니다.
            """
        )

    return base_inp, result
