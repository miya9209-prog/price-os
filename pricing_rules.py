from dataclasses import dataclass


@dataclass(frozen=True)
class PricingDefaults:
    tax_rate: float = 4.0
    payment_fee_rate: float = 3.5
    packaging_rate: float = 1.0
    ad_rate: float = 10.0
    coupon_rate: float = 0.0
    target_multiple: float = 2.0
    expected_qty: int = 100
    target_contribution_margin: float = 20.0


GRADE_RULES = (
    (25.0, "A", "적극 판매 / 광고 확대 검토 가능"),
    (18.0, "B", "수익성 양호"),
    (12.0, "C", "판매 가능 / 관리 필요"),
    (5.0, "D", "수익성 위험"),
    (float("-inf"), "E", "가격·원가 재검토 필요"),
)


def grade_from_margin(contribution_margin_rate: float) -> tuple[str, str]:
    for threshold, grade, label in GRADE_RULES:
        if contribution_margin_rate >= threshold:
            return grade, label
    return "E", "가격·원가 재검토 필요"


def round_price(value: float, strategy: str = "800원 끝") -> int:
    """Round price transparently for Korean retail pricing.

    - 100원 단위: nearest 100 won
    - 900원 끝: nearest price ending in 900
    - 800원 끝: nearest price ending in 800
    The nearest candidate is selected; ties choose the higher price.
    """
    if value <= 0:
        return 0

    if strategy == "100원 단위":
        return int(round(value / 100.0) * 100)

    ending = 900 if strategy == "900원 끝" else 800
    base = int(value // 1000) * 1000
    candidates = [max(ending, base - 1000 + ending), base + ending, base + 1000 + ending]
    candidates = [c for c in candidates if c > 0]
    return min(candidates, key=lambda c: (abs(c - value), -c))
