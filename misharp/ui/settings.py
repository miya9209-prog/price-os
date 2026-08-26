from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import streamlit as st

from ..config import get_settings
from ..db import session_scope
from ..repositories import get_token
from ..connectors.cafe24_oauth import build_authorize_url
from ..connectors.cafe24_analytics import Cafe24AnalyticsClient
from ..services.query import daily_dataframe
from ..services.sync_daily import sync_cafe24_daily
from ..services.sync_hourly import sync_hourly
from ..services.sync_products import sync_product_sales
from .common import daily_report_guide, sync_status_bar, styled_numeric_table, render_report_table


def _is_set(value: str) -> bool:
    return bool(str(value or "").strip())


def _local_today():
    s = get_settings()
    return datetime.now(ZoneInfo(s.app_timezone)).date()


def _test_cafe24(day) -> dict:
    """DB에 쓰지 않고 Cafe24 Analytics 읽기 권한/토큰을 확인한다."""
    c = Cafe24AnalyticsClient()
    sales = c.sales_times(day)
    visitors = c.visitors(day, "day")
    carts = c.cart_actions(day)

    sales_amount = sum(float(x.get("order_amount") or 0) for x in sales)
    order_count = sum(int(float(x.get("order_count") or 0)) for x in sales)
    visit_count = sum(int(float(x.get("visit_count") or x.get("count") or 0)) for x in visitors)
    cart_count = sum(int(float(x.get("add_cart_count") or 0)) for x in carts)

    return {
        "기준일": day.isoformat(),
        "매출액": int(sales_amount),
        "주문수": order_count,
        "방문": visit_count,
        "장바구니": cart_count,
        "sales/times 응답행": len(sales),
        "visitors/view 응답행": len(visitors),
        "carts/action 응답행": len(carts),
    }


def _sync_cafe24_day(day) -> dict:
    daily = sync_cafe24_daily(day)
    products = sync_product_sales(day)
    hourly = sync_hourly(day)
    return {
        "date": daily.get("date", day.isoformat()),
        "상품행": products,
        "시간대행": hourly,
    }


def render() -> None:
    s = get_settings()
    with session_scope() as db:
        cafe24_token_saved = get_token(db, "cafe24") is not None

    st.title("데이터·설정")
    st.caption("Cafe24 Analytics를 공식 통계 원천으로 사용하고, 광고비·재고·앱·SERA 참고 데이터를 함께 연결합니다.")

    c1, c2, c3, c4 = st.columns(4)
    db_label = (
        f"PostgreSQL · {s.database_schema}"
        if str(s.database_url).startswith("postgresql")
        else "로컬 SQLite"
        if str(s.database_url).startswith("sqlite")
        else "미설정"
    )
    c1.metric("DB", db_label)
    c2.metric("Cafe24 Mall", s.cafe24_mall_id or "미설정")
    c3.metric("Cafe24 토큰", "저장됨" if cafe24_token_saved else "없음")
    c4.metric("광고비 시트", "설정됨" if _is_set(s.google_service_account_json) else "미설정")

    if str(s.database_url).startswith("postgresql"):
        st.caption(f"DB 분리: 같은 Supabase를 사용하되 `{s.database_schema}` schema에만 DAILY REPORT 테이블을 저장합니다.")

    st.subheader("연동 상태")
    sync_status_bar()

    st.subheader("1. Cafe24 API")
    st.caption("상품·주문·접속통계 권한을 최초 1회 승인합니다. 이후 Access Token은 Refresh Token으로 자동 갱신합니다.")
    st.code(
        s.cafe24_scopes or "mall.read_order mall.read_product mall.read_analytics mall.read_customer",
        language=None,
    )
    missing = [
        key
        for key, value in {
            "CAFE24_MALL_ID": s.cafe24_mall_id,
            "CAFE24_CLIENT_ID": s.cafe24_client_id,
            "CAFE24_CLIENT_SECRET": s.cafe24_client_secret,
            "CAFE24_REDIRECT_URI": s.cafe24_redirect_uri,
            "TOKEN_ENCRYPTION_KEY": s.token_encryption_key,
        }.items()
        if not _is_set(value)
    ]

    if missing:
        st.warning("Cafe24 인증 전 Secrets에 먼저 입력하세요: " + ", ".join(missing))
    else:
        if st.button("Cafe24 인증 링크 생성", use_container_width=False):
            try:
                st.session_state.cafe24_auth_url = build_authorize_url()
            except Exception as exc:
                st.error(f"인증 링크 생성 실패: {exc}")
        if st.session_state.get("cafe24_auth_url"):
            st.link_button("Cafe24 쇼핑몰 관리자 승인 열기", st.session_state.cafe24_auth_url)
        if cafe24_token_saved:
            st.success("Cafe24 OAuth 토큰이 DB에 암호화 저장되어 있습니다.")

            st.markdown("#### Cafe24 실데이터 확인")
            st.caption("다른 데이터원과 무관하게 Cafe24 Analytics만 단독으로 테스트·수집합니다.")

            today = _local_today()
            yesterday = today - timedelta(days=1)

            b1, b2, b3 = st.columns(3)

            if b1.button("Cafe24 연결 테스트", use_container_width=True):
                with st.spinner(f"{yesterday.isoformat()} Cafe24 Analytics를 확인하고 있습니다..."):
                    try:
                        result = _test_cafe24(yesterday)
                        st.success("Cafe24 Analytics 연결 정상")
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("테스트 매출", f"{result['매출액']:,}원")
                        m2.metric("주문", f"{result['주문수']:,}건")
                        m3.metric("방문", f"{result['방문']:,}")
                        m4.metric("장바구니", f"{result['장바구니']:,}")
                        st.caption(
                            f"기준일 {result['기준일']} · "
                            f"sales/times {result['sales/times 응답행']}행 · "
                            f"visitors/view {result['visitors/view 응답행']}행 · "
                            f"carts/action {result['carts/action 응답행']}행"
                        )
                    except Exception as exc:
                        st.error(f"Cafe24 연결 테스트 실패: {exc}")

            if b2.button("어제 Cafe24 데이터 수집", use_container_width=True):
                with st.spinner(f"{yesterday.isoformat()} 일별·상품·시간대 데이터를 저장하고 있습니다..."):
                    try:
                        result = _sync_cafe24_day(yesterday)
                        st.success(
                            f"{result['date']} 수집 완료 · 상품 {result['상품행']:,}행 · 시간대 {result['시간대행']:,}행"
                        )
                        df = daily_dataframe(yesterday, yesterday)
                        if not df.empty:
                            render_report_table(df)
                    except Exception as exc:
                        st.error(f"어제 Cafe24 데이터 수집 실패: {exc}")

            if b3.button("오늘 Cafe24 데이터 수집", use_container_width=True):
                with st.spinner(f"{today.isoformat()} 현재까지 데이터를 저장하고 있습니다..."):
                    try:
                        result = _sync_cafe24_day(today)
                        st.success(
                            f"{result['date']} 현재까지 수집 완료 · 상품 {result['상품행']:,}행 · 시간대 {result['시간대행']:,}행"
                        )
                        df = daily_dataframe(today, today)
                        if not df.empty:
                            render_report_table(df)
                        st.info("오늘 데이터는 진행 중 집계입니다. 다음 자동수집에서 같은 날짜가 다시 갱신됩니다.")
                    except Exception as exc:
                        st.error(f"오늘 Cafe24 데이터 수집 실패: {exc}")

    st.subheader("2. 외부 데이터 준비 상태")
    rows = [
        {
            "데이터": "Google 광고비 Sheet",
            "상태": "준비" if _is_set(s.google_service_account_json) else "미설정",
            "필요값": "GOOGLE_SERVICE_ACCOUNT_JSON / AD_SHEET_ID / AD_SHEET_GID",
        },
        {
            "데이터": "Sellmate 재고·택배",
            "상태": "준비" if _is_set(s.sellmate_api_base_url) and _is_set(s.sellmate_api_key) else "API 정보 필요",
            "필요값": "Base URL / API Key / 재고 endpoint / 출고 endpoint / JSON 샘플",
        },
        {
            "데이터": "iApps 앱 통계",
            "상태": "준비" if _is_set(s.iapps_api_base_url) and _is_set(s.iapps_api_key) else "API 정보 필요",
            "필요값": "Base URL / API Key / 일별 설치·DAU endpoint",
        },
        {
            "데이터": "SERA",
            "상태": "참고 연동",
            "필요값": "현재는 SERA 보고서 importer / 자동 API 제공 시 connector 교체",
        },
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.subheader("3. 운영 원칙")
    st.markdown(
        """
- **공식 매출·유입·상품 성과:** Cafe24 Analytics API
- **일별 광고비:** 지정 Google Sheet
- **옵션별 현재고·택배수량:** Sellmate API
- **앱 설치·앱 순방문:** iApps API 또는 자동 Export 연동
- **SERA:** 실시간 참고·교차검증용. 공식 집계와 혼합하지 않음
- **과거 비교:** 기존 월별 일일보고를 최초 1회 DB로 이관
        """
    )

    daily_report_guide()
