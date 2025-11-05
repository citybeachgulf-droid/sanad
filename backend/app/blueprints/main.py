from flask import Blueprint, render_template
from ..models import Customer, Ticket, Invoice

main_bp = Blueprint('main', __name__)

@main_bp.get('/')
def dashboard():
    stats = {
        'customers': Customer.query.count(),
        'tickets': Ticket.query.count(),
        'invoices': Invoice.query.count(),
    }
    return render_template('dashboard.html', stats=stats)
