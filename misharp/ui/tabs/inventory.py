from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from ...config import get_settings
from ...services.export_xlsx import dataframe_to_xlsx
from ...services.query import inventory_dataframe
from ..common import styled_numeric_table, render_report_table


def _default_season_end(end: date) -> date:
    raw = get_settings().season_end_date
    if raw:
        try: return date.fromisoformat(raw)
        except ValueError: pass
    # 현재가 여름이면 8/31, 아니면 60일 후를 안전한 기본값으로 사용
    return date(end.year, 8, 31) if end.month <= 8 else end + timedelta(days=60)


def render(_: date, end: date) -> None:
    season_end = st.date_input("시즌 종료 기준일", value=max(_default_season_end(end), end))
    df = inventory_dataframe(end, season_end)
    if df.empty:
        st.info("셀메이트 재고 데이터가 아직 없습니다. API 승인 후 Sellmate 어댑터를 연결하면 활성화됩니다."); return
    c1, c2, c3 = st.columns(3)
    min_stock = c1.number_input("재고수량 기준", min_value=0, value=10, step=1)
    status = c2.multiselect("재고상태", sorted(df["재고상태"].dropna().unique().tolist()))
    sort_col = c3.selectbox("정렬", ["판매가능재고", "소진속도달성률(%)", "예상 소진일", "최근30일 판매"])
    view = df[pd.to_numeric(df["판매가능재고"], errors="coerce").fillna(0) >= min_stock].copy()
    if status: view = view[view["재고상태"].isin(status)]
    view = view.sort_values(sort_col, ascending=(sort_col in ["소진속도달성률(%)", "최근30일 판매"]), na_position="last")
    view.insert(0, "순위", range(1, len(view)+1))
    render_report_table(view, max_height=700)
    st.download_button("주요 재고 현황 XLSX 다운로드", data=dataframe_to_xlsx(view, "주요재고현황"),
        file_name=f"미샵_주요재고현황_{end:%Y%m%d}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
