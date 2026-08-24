"""Cafe24 integration placeholder.

V1 intentionally keeps Cafe24 disconnected so the pricing formula can be validated first.
Later this module can fetch product_no, product_name, supply_price, price, category and images.
"""


def cafe24_status() -> dict:
    return {
        "connected": False,
        "message": "V1 미연동 — 가격 계산식 검증 후 Cafe24 Admin API를 연결합니다.",
    }
