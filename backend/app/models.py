from datetime import datetime
from .extensions import db

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    national_id = db.Column(db.String(32), unique=True)
    phone = db.Column(db.String(32))
    email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    gov_entity = db.Column(db.String(120))
    office_fee = db.Column(db.Numeric(10,2), default=0)
    gov_fee_type = db.Column(db.String(10), default='fixed')  # fixed/variable
    gov_fee_value = db.Column(db.Numeric(10,2), default=0)
    vat_applicable = db.Column(db.Boolean, default=True)

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'))
    status = db.Column(db.String(32), default='New')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    customer = db.relationship('Customer')
    service = db.relationship('Service')

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'))
    subtotal_office_fee = db.Column(db.Numeric(10,2), default=0)
    total_gov_fees = db.Column(db.Numeric(10,2), default=0)
    vat_amount = db.Column(db.Numeric(10,2), default=0)
    grand_total = db.Column(db.Numeric(10,2), default=0)
    status = db.Column(db.String(32), default='Unpaid')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    customer = db.relationship('Customer')
    ticket = db.relationship('Ticket')

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'))
    qty = db.Column(db.Integer, default=1)
    office_fee = db.Column(db.Numeric(10,2), default=0)
    gov_fee = db.Column(db.Numeric(10,2), default=0)
    vat_amount = db.Column(db.Numeric(10,2), default=0)
    line_total = db.Column(db.Numeric(10,2), default=0)

    invoice = db.relationship('Invoice', backref='items')
    service = db.relationship('Service')
