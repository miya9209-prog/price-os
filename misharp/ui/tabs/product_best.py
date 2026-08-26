from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from ...services.export_xlsx import dataframe_to_xlsx
from ...services.query import product_sales_dataframe
from ..common import styled_numeric_table, render_report_table


def render(start: date, end: date) -> None:
    df = product_sales_dataframe(start, end)
    if df.empty:
        st.info("선택기간 상품 데이터가 없습니다. Cafe24 상품/장바구니 동기화를 먼저 실행하세요."); return
    c1, c2, c3 = st.columns(3)
    sort_label = c1.selectbox("정렬", ["실결제 매출", "판매수량", "판매건수", "상품 조회수", "장바구니", "구매전환율(%)"])
    decisions = sorted(df["자동판정"].dropna().unique().tolist())
    selected = c2.multiselect("자동판정", decisions)
    top_n = c3.selectbox("표시 상품", [20, 50, 100, "전체"], index=1)
    keyword = st.text_input("상품명 검색", placeholder="상품명을 입력하세요")
    view = df.copy()
    if keyword: view = view[view["상품명"].str.contains(keyword, case=False, na=False)]
    if selected: view = view[view["자동판정"].isin(selected)]
    view = view.sort_values(sort_label, ascending=False, na_position="last")
    if top_n != "전체": view = view.head(int(top_n))
    view.insert(0, "순위", range(1, len(view)+1))
    st.caption("SERA 값은 실시간 참고/검증용 스냅샷이며, 공식 집계 기준은 Cafe24 Analytics API입니다.")
    render_report_table(view, max_height=700)
    st.download_button("상품 판매 베스트 XLSX 다운로드", data=dataframe_to_xlsx(view, "상품판매베스트"),
        file_name=f"미샵_상품판매베스트_{start:%Y%m%d}_{end:%Y%m%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
