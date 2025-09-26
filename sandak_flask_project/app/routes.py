from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Client, Transaction, Payment, Ministry, Service, TransactionRecord
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


# Government transactions - add page
@main_bp.route('/gov/transactions/new', methods=['GET', 'POST'])
@login_required
def add_gov_transaction():
    if request.method == 'POST':
        client_name = request.form.get('client_name', '').strip()
        ministry_id = request.form.get('ministry_id')
        service_id = request.form.get('service_id')
        notes = request.form.get('notes')

        if not client_name or not ministry_id or not service_id:
            flash('الرجاء تعبئة جميع الحقول المطلوبة', 'danger')
            ministries = Ministry.query.order_by(Ministry.name).all()
            return render_template('add_transaction.html', ministries=ministries)

        rec = TransactionRecord(
            client_name=client_name,
            ministry_id=int(ministry_id),
            service_id=int(service_id),
            notes=notes,
            employee_id=current_user.id,
        )
        db.session.add(rec)
        db.session.commit()
        flash('تم حفظ المعاملة بنجاح', 'success')
        return redirect(url_for('main.dashboard'))

    ministries = Ministry.query.order_by(Ministry.name).all()
    return render_template('add_transaction.html', ministries=ministries)


# Services API for dependent dropdown
@main_bp.route('/api/services')
@login_required
def api_services_by_ministry():
    ministry_id = request.args.get('ministry_id', type=int)
    if not ministry_id:
        return jsonify([])
    items = Service.query.filter_by(ministry_id=ministry_id).order_by(Service.name).all()
    return jsonify([{'id': s.id, 'name': s.name} for s in items])
