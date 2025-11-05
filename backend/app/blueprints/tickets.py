from flask import Blueprint, render_template, request, redirect, url_for
from ..extensions import db
from ..models import Ticket, Customer, Service

tickets_bp = Blueprint('tickets', __name__)

@tickets_bp.get('/')
def list_tickets():
    rows = Ticket.query.order_by(Ticket.id.desc()).all()
    return render_template('tickets/list.html', rows=rows)

@tickets_bp.get('/new')
def new_ticket():
    customers = Customer.query.all()
    services = Service.query.all()
    return render_template('tickets/form.html', customers=customers, services=services)

@tickets_bp.post('/new')
def create_ticket():
    t = Ticket(
        customer_id=request.form['customer_id'],
        service_id=request.form['service_id'],
        notes=request.form.get('notes')
    )
    db.session.add(t)
    db.session.commit()
    return redirect(url_for('tickets.list_tickets'))
