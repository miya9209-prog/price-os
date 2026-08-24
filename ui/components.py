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


def red_metric_card(label: str, value: str, note: str | None = None):
    note_html = f'<div class="misharp-red-metric-note">{note}</div>' if note else ''
    st.markdown(
        f"""
        <div class="misharp-red-metric">
            <div class="misharp-red-metric-label">{label}</div>
            <div class="misharp-red-metric-value">{value}</div>
            {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
