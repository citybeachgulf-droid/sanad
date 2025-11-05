from decimal import Decimal, ROUND_HALF_UP
from flask import current_app

TWOPLACES = Decimal('0.01')

def calc_vat(amount: Decimal) -> Decimal:
    rate = Decimal(str(current_app.config.get('VAT_RATE', 0.05)))
    return (Decimal(amount) * rate).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

def new_pricing_ctx():
    return {
        'subtotal_office_fee': Decimal('0.00'),
        'total_gov_fees': Decimal('0.00'),
        'vat_amount': Decimal('0.00'),
        'grand_total': Decimal('0.00'),
    }

def add_item(pricing_ctx, service, qty: int = 1, variable_input: Decimal | None = None):
    office_fee = Decimal(str(service.office_fee)) * qty
    if service.gov_fee_type == 'variable' and variable_input is not None:
        gov_fee = Decimal(str(variable_input))
    else:
        gov_fee = Decimal(str(service.gov_fee_value)) * qty

    vat_amount = calc_vat(office_fee) if service.vat_applicable else Decimal('0.00')
    line_total = (office_fee + vat_amount + gov_fee).quantize(TWOPLACES)

    pricing_ctx['subtotal_office_fee'] += office_fee
    pricing_ctx['total_gov_fees'] += gov_fee
    pricing_ctx['vat_amount'] += vat_amount
    pricing_ctx['grand_total'] += line_total

    return {
        'qty': qty,
        'office_fee': office_fee,
        'gov_fee': gov_fee,
        'vat_amount': vat_amount,
        'line_total': line_total
    }
