import streamlit as st


def won(value: float) -> str:
    return f"{value:,.0f}원"


def pct(value: float) -> str:
    return f"{value:.1f}%"


def metric_card(label: str, value: str, help_text: str | None = None):
    st.metric(label, value, help=help_text)


def grade_badge(grade: str, label: str):
    emoji = {"A": "🟢", "B": "🟢", "C": "🟡", "D": "🟠", "E": "🔴"}.get(grade, "⚪")
    st.markdown(f"### {emoji} 공헌이익 등급 {grade}")
    st.caption(label)
