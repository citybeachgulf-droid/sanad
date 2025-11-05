from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for
from ..extensions import db
from ..models import Invoice, InvoiceItem, Ticket, Service
from ..accounting import new_pricing_ctx, add_item

invoices_bp = Blueprint('invoices', __name__)

@invoices_bp.get('/new/<int:ticket_id>')
def new_invoice(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    return render_template('invoices/pos.html', ticket=ticket)

@invoices_bp.post('/create')
def create_invoice():
    ticket_id = int(request.form['ticket_id'])
    service_id = int(request.form['service_id'])
    qty = int(request.form.get('qty', 1))
    variable_input = request.form.get('variable_input')
    variable_input = Decimal(variable_input) if variable_input else None

    ticket = Ticket.query.get_or_404(ticket_id)
    service = Service.query.get_or_404(service_id)

    ctx = new_pricing_ctx()
    item_ctx = add_item(ctx, service, qty, variable_input)

    inv = Invoice(
        customer_id=ticket.customer_id,
        ticket_id=ticket.id,
        subtotal_office_fee=ctx['subtotal_office_fee'],
        total_gov_fees=ctx['total_gov_fees'],
        vat_amount=ctx['vat_amount'],
        grand_total=ctx['grand_total'],
        status='Unpaid'
    )
    db.session.add(inv)
    db.session.flush()

    item = InvoiceItem(
        invoice_id=inv.id,
        service_id=service.id,
        qty=qty,
        office_fee=item_ctx['office_fee'],
        gov_fee=item_ctx['gov_fee'],
        vat_amount=item_ctx['vat_amount'],
        line_total=item_ctx['line_total']
    )
    db.session.add(item)
    db.session.commit()

    return redirect(url_for('invoices.show_invoice', invoice_id=inv.id))

@invoices_bp.get('/<int:invoice_id>')
def show_invoice(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    return render_template('invoices/show.html', inv=inv)
