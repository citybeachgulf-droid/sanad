from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import User, Client, Transaction, Payment
from app.forms import ClientForm, TransactionForm

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    # basic stats
    total_clients = Client.query.count()
    total_transactions = Transaction.query.count()
    pending = Transaction.query.filter_by(status='pending').count()
    return render_template('dashboard.html', total_clients=total_clients, total_transactions=total_transactions, pending=pending)


@main_bp.route('/clients')
@login_required
def clients():
    clients = Client.query.order_by(Client.created_at.desc()).all()
    return render_template('clients.html', clients=clients)


@main_bp.route('/clients/new', methods=['GET','POST'])
@login_required
def new_client():
    form = ClientForm()
    if form.validate_on_submit():
        c = Client(name=form.name.data, phone=form.phone.data, email=form.email.data, national_id=form.national_id.data)
        db.session.add(c)
        db.session.commit()
        flash('Client created.')
        return redirect(url_for('main.clients'))
    return render_template('client_form.html', form=form)


@main_bp.route('/transactions/new', methods=['GET','POST'])
@login_required
def new_transaction():
    form = TransactionForm()
    if form.validate_on_submit():
        t = Transaction(client_id=int(form.client_id.data), service_type=form.service_type.data, office=form.office.data, fee=form.fee.data or 0, details=form.details.data)
        db.session.add(t)
        db.session.commit()
        flash('Transaction created.')
        return redirect(url_for('main.dashboard'))
    return render_template('transaction_form.html', form=form)
