from pricing_engine import PricingInput, calculate_pricing


def test_basic_positive_margin():
    r = calculate_pricing(PricingInput(product_cost=18000, target_multiple=2.8))
    assert r.list_price > 0
    assert r.paid_price > 0
    assert r.contribution_profit != 0
    assert r.grade in {"A", "B", "C", "D", "E"}


def test_coupon_reduces_profit():
    base = calculate_pricing(PricingInput(product_cost=18000, coupon_rate=0))
    discounted = calculate_pricing(PricingInput(product_cost=18000, coupon_rate=20))
    assert discounted.contribution_profit < base.contribution_profit


def test_ad_rate_reduces_profit():
    low = calculate_pricing(PricingInput(product_cost=18000, ad_rate=8))
    high = calculate_pricing(PricingInput(product_cost=18000, ad_rate=15))
    assert high.contribution_profit < low.contribution_profit
