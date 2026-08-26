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


def slider_scale(labels: list[str]):
    """Render reference labels at the exact proportional slider positions.

    Each label is anchored by percentage instead of flex spacing, so values with
    different text widths (for example 5 and 10) stay centered under the same
    slider position.
    """
    if not labels:
        return

    if len(labels) == 1:
        positions = [50.0]
    else:
        positions = [i * 100 / (len(labels) - 1) for i in range(len(labels))]

    cells = "".join(
        f'<span class="misharp-scale-label" style="left:{pos:.6f}%">{label}</span>'
        for label, pos in zip(labels, positions)
    )
    st.markdown(
        f"""
        <div class="misharp-slider-scale" aria-hidden="true">
            {cells}
        </div>
        """,
        unsafe_allow_html=True,
    )

