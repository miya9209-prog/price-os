from __future__ import annotations

from zoneinfo import ZoneInfo
import html

import pandas as pd
import streamlit as st

from ..config import get_settings
from ..db import session_scope
from ..repositories import latest_sync_runs


def display_missing(df: pd.DataFrame) -> pd.DataFrame:
    return df.astype(object).where(pd.notna(df), "자료없음")


_RATE_HINTS = (
    "%", "율", "비율", "전환", "ROAS", "CTR", "CVR",
    "OpV", "ESpV", "달성률",
)
_FORCE_WHOLE_HINTS = (
    "매출", "실결제", "광고비", "객단가", "주문", "건수", "수량",
    "방문", "조회", "장바구니", "재고", "판매", "회원가입", "설치수",
    "페이지뷰", "순위", "시간", "시즌남은일",
)
_FORCE_DECIMAL_HINTS = (
    "일평균", "필요일판매", "예상 소진일",
)


def _is_rate_col(name: str) -> bool:
    label = str(name)
    return any(h in label for h in _RATE_HINTS)


def _is_force_decimal_col(name: str) -> bool:
    label = str(name)
    return any(h in label for h in _FORCE_DECIMAL_HINTS)


def _is_force_whole_col(name: str) -> bool:
    label = str(name)
    if _is_rate_col(label) or _is_force_decimal_col(label):
        return False
    return any(h in label for h in _FORCE_WHOLE_HINTS)


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    cols: list[str] = []
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_numeric_dtype(s):
            cols.append(col)
            continue
        # object dtype라도 실제 값 대부분이 숫자이면 숫자 열로 처리
        non_null = s.dropna()
        if non_null.empty:
            continue
        converted = pd.to_numeric(non_null, errors="coerce")
        if converted.notna().all():
            cols.append(col)
    return cols


def _column_needs_decimals(series: pd.Series, column_name: str) -> bool:
    if _is_rate_col(column_name) or _is_force_decimal_col(column_name):
        return True
    if _is_force_whole_col(column_name):
        return False

    nums = pd.to_numeric(series, errors="coerce").dropna()
    if nums.empty:
        return False
    # 실제 소수값이 존재하는 일반 숫자 열은 2자리까지 표시
    return bool(((nums - nums.round()).abs() > 1e-9).any())


def styled_numeric_table(
    df: pd.DataFrame,
    *,
    comparison_mode: bool = False,
):
    """MISHARP DAILY REPORT 공통 표 표시 규칙.

    - 모든 숫자 셀: 오른쪽 정렬
    - 금액/건수/수량 등: 1,000단위 콤마 + 소수점 없음
    - 비율/전환율 및 의미 있는 소수값: 소수점 둘째 자리
    - 결측값: 자료없음
    - comparison_mode=True이면 '증감' 행은 전부 소수점 둘째 자리로 표시
      (비율열은 %p, 나머지는 %)
    """
    if df is None or df.empty:
        return df

    raw = df.copy()
    numeric_cols = _numeric_columns(raw)
    out = raw.copy()

    growth_rows: set = set()
    if comparison_mode:
        for idx in out.index:
            label = str(out.at[idx, "비교구분"]) if "비교구분" in out.columns else str(idx)
            if "증감" in label:
                growth_rows.add(idx)

    for col in numeric_cols:
        decimals = _column_needs_decimals(raw[col], col)

        def _fmt(v, *, _col=col, _decimals=decimals, _idx=None):
            if v is None or pd.isna(v):
                return "자료없음"
            num = float(v)
            if comparison_mode and _idx in growth_rows:
                suffix = "%p" if _is_rate_col(_col) else "%"
                return f"{num:+,.2f}{suffix}"
            return f"{num:,.2f}" if _decimals else f"{num:,.0f}"

        # row index가 필요한 comparison_mode는 list comprehension으로 처리
        if comparison_mode:
            out[col] = [
                _fmt(v, _idx=idx) for idx, v in zip(out.index, out[col].tolist())
            ]
        else:
            out[col] = out[col].map(lambda v: _fmt(v))

    # 숫자열 외 결측값도 자료없음으로 통일
    for col in out.columns:
        if col not in numeric_cols:
            out[col] = out[col].astype(object).where(pd.notna(out[col]), "자료없음")

    styler = out.style
    if numeric_cols:
        styler = styler.set_properties(
            subset=pd.IndexSlice[:, numeric_cols],
            **{"text-align": "right"},
        )
    return styler


def sync_status_bar() -> None:
    with session_scope() as db:
        rows = latest_sync_runs(db)
    if not rows:
        st.markdown('<div class="mso-status">아직 자동수집 실행 기록이 없습니다.</div>', unsafe_allow_html=True)
        return
    tz = ZoneInfo(get_settings().app_timezone)
    label = {
        "cafe24_daily": "카페24 일별",
        "cafe24_products": "카페24 상품",
        "cafe24_hourly": "카페24 시간대",
        "google_adsheet": "광고비시트",
        "sellmate": "셀메이트",
        "iapps": "아이앱스",
        "sera_reference": "SERA 참고",
    }
    parts = []
    for r in rows:
        icon = "●" if r.status == "success" else "▲"
        dt = r.finished_at or r.started_at
        if dt.tzinfo is None:
            when = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz).strftime("%m-%d %H:%M")
        else:
            when = dt.astimezone(tz).strftime("%m-%d %H:%M")
        parts.append(f"{icon} {label.get(r.source, r.source)} {when}")
    st.markdown(f'<div class="mso-status">{" &nbsp;·&nbsp; ".join(parts)}</div>', unsafe_allow_html=True)


def daily_report_guide() -> None:
    with st.expander("MISHARP DAILY REPORT 이용방법 · 처음 세팅할 때 꼭 읽어주세요", expanded=False):
        st.markdown(
            """
            <div class="mso-guide-intro">
            MISHARP DAILY REPORT는 <b>매출·유입·전환·상품·재고·앱 통계</b>를 한곳에 모으고,
            전년·전전년 비교와 매출 회복 경보를 통해 <b>오늘 어디를 먼저 봐야 하는지</b> 판단하기 위한 경영 리포트입니다.
            </div>
            <div class="mso-guide-step"><b>1. 일별 종합통계</b><br>기간을 선택하면 실결제, 주문, 객단가, 방문, 전환율, 광고비와 상품조회 → 장바구니 → 주문 퍼널을 확인합니다. 하단에는 전년도·전전년도 동일기간 비교가 자동 표시됩니다.</div>
            <div class="mso-guide-step"><b>2. 상품 판매 베스트</b><br>Cafe24 Analytics의 조회·장바구니·판매·매출을 상품번호 기준으로 합산하고, 재고와 함께 매출확대 / 재고회수 / CRM회수 / 상세개선 후보를 표시합니다.</div>
            <div class="mso-guide-step"><b>3. 주요 재고 현황</b><br>Sellmate의 옵션별 판매가능재고와 최근 판매속도를 기준으로 예상 소진일과 시즌 종료일까지 필요한 일판매량을 계산합니다.</div>
            <div class="mso-guide-step"><b>4. 데이터 기준</b><br>공식 매출·상품 성과는 Cafe24 Analytics를 기준으로 합니다. SERA는 실시간 참고·검증용이며, 광고비는 Google Sheet, 재고는 Sellmate, 앱 통계는 iApps를 기준으로 연결합니다.</div>
            <div class="mso-guide-step"><b>5. 데이터가 비어 있을 때</b><br><b>데이터·설정</b>에서 각 연동 상태를 먼저 확인합니다. 값 0과 미수집을 구분하기 위해 수집되지 않은 값은 <b>자료없음</b>으로 표시합니다.</div>
            """,
            unsafe_allow_html=True,
        )


def _try_number(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text == "자료없음":
        return None
    text = text.replace(",", "")
    try:
        return float(text)
    except Exception:
        return None


def _format_report_cell(value, column_name: str, *, growth_row: bool = False):
    if value is None or pd.isna(value):
        return "자료없음", False

    num = _try_number(value)
    if num is None:
        return str(value), False

    if growth_row:
        suffix = "%p" if _is_rate_col(column_name) else "%"
        return f"{num:+,.2f}{suffix}", True

    if _is_rate_col(column_name) or _is_force_decimal_col(column_name):
        return f"{num:,.2f}", True

    if _is_force_whole_col(column_name):
        return f"{num:,.0f}", True

    # 의미 있는 소수값은 2자리, 정수형 값은 소수점 없이
    if abs(num - round(num)) > 1e-9:
        return f"{num:,.2f}", True
    return f"{num:,.0f}", True


def render_report_table(
    df: pd.DataFrame,
    *,
    comparison_mode: bool = False,
    max_height: int = 620,
) -> None:
    """Streamlit grid 정렬 제약을 피하기 위한 DAILY REPORT 공통 HTML 표.

    숫자 셀은 실제 HTML td에 text-align:right를 직접 적용하므로
    일별/비교/상품/재고 표에서 항상 오른쪽 정렬된다.
    """
    if df is None or df.empty:
        st.info("표시할 데이터가 없습니다.")
        return

    table = df.copy()

    css = f"""
    <style>
      .mdr-table-wrap {{
        width: 100%;
        overflow-x: auto;
        overflow-y: auto;
        max-height: {int(max_height)}px;
        border: 1px solid #e6e8eb;
        border-radius: 4px;
        background: white;
      }}
      table.mdr-table {{
        width: max-content;
        min-width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 13px;
        color: #262730;
      }}
      table.mdr-table thead th {{
        position: sticky;
        top: 0;
        z-index: 2;
        background: #f7f8fa;
        color: #68707a;
        font-weight: 500;
        text-align: left;
        white-space: nowrap;
        padding: 9px 10px;
        border-bottom: 1px solid #e6e8eb;
        border-right: 1px solid #eceef1;
      }}
      table.mdr-table tbody td {{
        white-space: nowrap;
        padding: 9px 10px;
        border-bottom: 1px solid #eceef1;
        border-right: 1px solid #eceef1;
        vertical-align: middle;
        text-align: left;
      }}
      table.mdr-table tbody td.mdr-num {{
        text-align: right !important;
        font-variant-numeric: tabular-nums;
      }}
      table.mdr-table tbody tr:last-child td {{
        border-bottom: 0;
      }}
      table.mdr-table th:last-child,
      table.mdr-table td:last-child {{
        border-right: 0;
      }}
    </style>
    """

    headers = "".join(
        f"<th>{html.escape(str(col))}</th>"
        for col in table.columns
    )

    body_rows = []
    for idx, row in table.iterrows():
        growth_row = False
        if comparison_mode:
            label = (
                str(row.get("비교구분", ""))
                if "비교구분" in table.columns
                else str(idx)
            )
            growth_row = "증감" in label

        cells = []
        for col in table.columns:
            value = row[col]
            text, is_num = _format_report_cell(
                value,
                str(col),
                growth_row=growth_row,
            )
            cls = ' class="mdr-num"' if is_num else ""
            cells.append(f"<td{cls}>{html.escape(text)}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    markup = (
        css
        + '<div class="mdr-table-wrap">'
        + '<table class="mdr-table">'
        + f"<thead><tr>{headers}</tr></thead>"
        + "<tbody>"
        + "".join(body_rows)
        + "</tbody></table></div>"
    )
    st.markdown(markup, unsafe_allow_html=True)
