from dataclasses import dataclass, asdict
from typing import Optional

from pricing_rules import grade_from_margin, round_price


@dataclass
class PricingInput:
    product_cost: float
    cost_vat_included: bool = True
    target_multiple: float = 2.8
    tax_rate: float = 4.0
    payment_fee_rate: float = 3.5
    packaging_rate: float = 1.0
    ad_rate: float = 10.0
    coupon_rate: float = 0.0
    expected_qty: int = 100
    competitor_avg_price: Optional[float] = None
    price_rounding: str = "800원 끝"
    manual_list_price: Optional[float] = None


@dataclass
class PricingResult:
    raw_target_price: float
    list_price: float
    discount_amount: float
    paid_price: float
    product_cash_cost: float
    product_net_cost: float
    input_vat: float
    output_vat: float
    vat_payable: float
    tax_cost: float
    payment_fee_cost: float
    packaging_cost: float
    ad_cost: float
    contribution_profit: float
    contribution_margin_rate: float
    total_contribution_profit: float
    grade: str
    grade_label: str
    competitor_gap_amount: Optional[float]
    competitor_gap_rate: Optional[float]
    max_ad_rate_before_loss: float
    max_coupon_rate_before_loss: float
    recommended_max_ad_rate: float
    recommended_max_discount_rate: float

    def to_dict(self):
        return asdict(self)


def _normalize_cost(product_cost: float, cost_vat_included: bool):
    if cost_vat_included:
        cash_cost = product_cost
        net_cost = product_cost / 1.1
        input_vat = product_cost - net_cost
    else:
        net_cost = product_cost
        input_vat = product_cost * 0.1
        cash_cost = product_cost + input_vat
    return cash_cost, net_cost, input_vat


def _contribution_at_coupon(inp: PricingInput, coupon_rate: float, ad_rate: Optional[float] = None) -> float:
    raw_target = inp.product_cost * inp.target_multiple
    list_price = float(inp.manual_list_price or round_price(raw_target, inp.price_rounding))
    paid = list_price * (1 - coupon_rate / 100.0)
    cash_cost, _, input_vat = _normalize_cost(inp.product_cost, inp.cost_vat_included)
    output_vat = paid / 11.0
    vat_payable = max(output_vat - input_vat, 0.0)
    actual_ad_rate = inp.ad_rate if ad_rate is None else ad_rate
    other = paid * ((inp.tax_rate + inp.payment_fee_rate + inp.packaging_rate + actual_ad_rate) / 100.0)
    return paid - cash_cost - vat_payable - other



def _margin_at_coupon(inp: PricingInput, coupon_rate: float, ad_rate: Optional[float] = None) -> float:
    raw_target = inp.product_cost * inp.target_multiple
    list_price = float(inp.manual_list_price or round_price(raw_target, inp.price_rounding))
    paid = list_price * (1 - coupon_rate / 100.0)
    if paid <= 0:
        return -100.0
    contribution = _contribution_at_coupon(inp, coupon_rate, ad_rate)
    return contribution / paid * 100.0


def _find_max_discount_for_target_margin(inp: PricingInput, target_margin: float, max_discount: float = 50.0) -> float:
    """Largest discount rate that still preserves the target contribution margin.

    Search is intentionally capped at the UI's maximum discount range (50%).
    """
    if _margin_at_coupon(inp, 0.0) < target_margin:
        return 0.0
    if _margin_at_coupon(inp, max_discount) >= target_margin:
        return max_discount
    lo, hi = 0.0, max_discount
    for _ in range(50):
        mid = (lo + hi) / 2
        if _margin_at_coupon(inp, mid) >= target_margin:
            lo = mid
        else:
            hi = mid
    return lo


def _find_max_coupon(inp: PricingInput) -> float:
    if _contribution_at_coupon(inp, 0) <= 0:
        return 0.0
    if _contribution_at_coupon(inp, 50) > 0:
        return 50.0
    lo, hi = 0.0, 50.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if _contribution_at_coupon(inp, mid) >= 0:
            lo = mid
        else:
            hi = mid
    return lo


def calculate_pricing(inp: PricingInput) -> PricingResult:
    raw_target = inp.product_cost * inp.target_multiple
    list_price = float(inp.manual_list_price or round_price(raw_target, inp.price_rounding))
    discount_amount = list_price * (inp.coupon_rate / 100.0)
    paid_price = list_price - discount_amount

    product_cash_cost, product_net_cost, input_vat = _normalize_cost(
        inp.product_cost, inp.cost_vat_included
    )

    # Consumer selling price is treated as VAT-included. Input VAT is credited when available.
    output_vat = paid_price / 11.0
    vat_payable = max(output_vat - input_vat, 0.0)

    tax_cost = paid_price * (inp.tax_rate / 100.0)
    payment_fee_cost = paid_price * (inp.payment_fee_rate / 100.0)
    packaging_cost = paid_price * (inp.packaging_rate / 100.0)
    ad_cost = paid_price * (inp.ad_rate / 100.0)

    contribution_profit = (
        paid_price
        - product_cash_cost
        - vat_payable
        - tax_cost
        - payment_fee_cost
        - packaging_cost
        - ad_cost
    )
    contribution_margin_rate = (contribution_profit / paid_price * 100.0) if paid_price else -100.0
    total_contribution_profit = contribution_profit * max(inp.expected_qty, 0)
    grade, grade_label = grade_from_margin(contribution_margin_rate)

    competitor_gap_amount = None
    competitor_gap_rate = None
    if inp.competitor_avg_price and inp.competitor_avg_price > 0:
        competitor_gap_amount = list_price - inp.competitor_avg_price
        competitor_gap_rate = competitor_gap_amount / inp.competitor_avg_price * 100.0

    # Maximum advertising rate before contribution profit reaches zero, under current coupon.
    fixed_ex_ad = paid_price - product_cash_cost - vat_payable - tax_cost - payment_fee_cost - packaging_cost
    max_ad_rate = max(0.0, fixed_ex_ad / paid_price * 100.0) if paid_price else 0.0

    max_coupon_rate = _find_max_coupon(inp)

    # Recommended operating limits: preserve the company's target contribution margin.
    # These are more practical than the theoretical break-even limits above.
    target_margin = 20.0
    recommended_max_ad_rate = max(0.0, max_ad_rate - target_margin)
    recommended_max_discount_rate = _find_max_discount_for_target_margin(
        inp, target_margin=target_margin, max_discount=50.0
    )

    return PricingResult(
        raw_target_price=raw_target,
        list_price=list_price,
        discount_amount=discount_amount,
        paid_price=paid_price,
        product_cash_cost=product_cash_cost,
        product_net_cost=product_net_cost,
        input_vat=input_vat,
        output_vat=output_vat,
        vat_payable=vat_payable,
        tax_cost=tax_cost,
        payment_fee_cost=payment_fee_cost,
        packaging_cost=packaging_cost,
        ad_cost=ad_cost,
        contribution_profit=contribution_profit,
        contribution_margin_rate=contribution_margin_rate,
        total_contribution_profit=total_contribution_profit,
        grade=grade,
        grade_label=grade_label,
        competitor_gap_amount=competitor_gap_amount,
        competitor_gap_rate=competitor_gap_rate,
        max_ad_rate_before_loss=max_ad_rate,
        max_coupon_rate_before_loss=max_coupon_rate,
        recommended_max_ad_rate=recommended_max_ad_rate,
        recommended_max_discount_rate=recommended_max_discount_rate,
    )


def build_why_diagnosis(inp: PricingInput, result: PricingResult) -> list[dict]:
    """Rule-based WHY diagnosis for V1. LLM/VOC evidence can replace or enrich this later."""
    items = []

    if result.contribution_profit < 0:
        items.append({
            "level": "위험",
            "title": "현재 조건에서는 판매할수록 손실이 발생합니다.",
            "reason": "원가와 변동비를 차감한 뒤 1장당 공헌이익이 음수입니다.",
            "action": "판매가 인상, 광고비 축소, 쿠폰 축소, 원가 재협상 중 최소 1개를 즉시 검토하세요.",
        })
    elif result.contribution_margin_rate < 12:
        items.append({
            "level": "주의",
            "title": "공헌이익 여유가 작습니다.",
            "reason": f"현재 공헌이익률이 {result.contribution_margin_rate:.1f}%로 D/E 위험구간에 가깝습니다.",
            "action": "쿠폰 또는 광고비가 추가 상승하기 전에 손익 방어선을 확인하세요.",
        })
    else:
        items.append({
            "level": "양호",
            "title": "현재 조건에서는 판매 가능한 수익성이 확보됩니다.",
            "reason": f"1장당 공헌이익 {result.contribution_profit:,.0f}원, 공헌이익률 {result.contribution_margin_rate:.1f}%입니다.",
            "action": "실제 판매 후 광고비율과 쿠폰율 변화를 기준으로 재검증하세요.",
        })

    cost_map = {
        "광고비": result.ad_cost,
        "세금평균": result.tax_cost,
        "결제수수료": result.payment_fee_cost,
        "포장비": result.packaging_cost,
        "부가세 부담": result.vat_payable,
    }
    biggest_name, biggest_value = max(cost_map.items(), key=lambda x: x[1])
    items.append({
        "level": "WHY",
        "title": f"현재 가장 큰 변동비 요인은 {biggest_name}입니다.",
        "reason": f"1장 기준 약 {biggest_value:,.0f}원이 반영됩니다.",
        "action": f"{biggest_name} 조건이 바뀔 때 공헌이익이 얼마나 변하는지 시뮬레이션하세요.",
    })

    if result.competitor_gap_rate is not None:
        if result.competitor_gap_rate > 8:
            msg = "경쟁사 평균보다 높은 편입니다. 가격 저항 가능성을 확인할 필요가 있습니다."
        elif result.competitor_gap_rate < -8:
            msg = "경쟁사 평균보다 낮은 편입니다. 가격을 더 받을 여지가 있는지 검토할 수 있습니다."
        else:
            msg = "경쟁사 평균과 유사한 가격대입니다."
        items.append({
            "level": "가격",
            "title": msg,
            "reason": f"경쟁사 평균 대비 {result.competitor_gap_rate:+.1f}% 차이입니다.",
            "action": "상품력·소재·사이즈·브랜드 차이를 함께 보고 최종 판매가를 결정하세요.",
        })

    return items
