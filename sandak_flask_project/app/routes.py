from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Client, Transaction, Payment, Ministry, Service, TransactionRecord, ManagedTransaction
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
        client_phone = (request.form.get('client_phone') or '').strip()
        ministry_id = request.form.get('ministry_id')
        service_id = request.form.get('service_id')
        notes = request.form.get('notes')

        if not client_name or not ministry_id or not service_id:
            flash('الرجاء تعبئة جميع الحقول المطلوبة', 'danger')
            ministries = Ministry.query.order_by(Ministry.name).all()
            return render_template('add_transaction.html', ministries=ministries)

        rec = TransactionRecord(
            client_name=client_name,
            client_phone=client_phone or None,
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


# ----------------------- Managed Transactions (Authority/Service catalog) -----------------------

AUTHORITIES = [
    'شرطة عمان السلطانية',
    'وزارة العمل',
    'وزارة التجارة والصناعة وترويج الاستثمار',
    'الهيئة العامة للتأمينات الاجتماعية',
    'وزارة الصحة',
    'وزارة الإسكان',
    'البلدية',
    'هيئة الكهرباء والمياه والاتصالات',
    'هيئة الاتصالات وتقنية المعلومات',
]

STATUSES = ['نشطة', 'معلقة', 'منتهية']


@main_bp.route('/transactions')
@login_required
def managed_transactions_list():
    authority = request.args.get('authority', '').strip()
    status = request.args.get('status', '').strip()

    query = ManagedTransaction.query
    if authority:
        query = query.filter(ManagedTransaction.authority == authority)
    if status:
        query = query.filter(ManagedTransaction.status == status)
    items = query.order_by(ManagedTransaction.created_at.desc()).all()

    return render_template(
        'transactions.html',
        items=items,
        authorities=AUTHORITIES,
        statuses=STATUSES,
        authority=authority,
        status=status,
    )


@main_bp.route('/transactions/add', methods=['POST'])
@login_required
def managed_transactions_add():
    authority = request.form.get('authority') or ''
    service = request.form.get('service') or ''
    description = request.form.get('description') or ''
    status = request.form.get('status') or 'نشطة'
    fee_raw = (request.form.get('fee') or '').strip()
    try:
        fee_value = float(fee_raw) if fee_raw != '' else 0.0
        if fee_value < 0:
            raise ValueError('negative fee')
    except Exception:
        flash('قيمة الرسوم غير صحيحة', 'danger')
        return redirect(url_for('main.managed_transactions_list'))

    if authority not in AUTHORITIES or not service or status not in STATUSES:
        flash('الرجاء تعبئة الحقول بشكل صحيح', 'danger')
        return redirect(url_for('main.managed_transactions_list'))

    row = ManagedTransaction(
        authority=authority,
        service=service.strip(),
        description=description.strip(),
        fee=fee_value,
        status=status,
    )
    db.session.add(row)
    db.session.commit()
    flash('تمت إضافة المعاملة', 'success')
    return redirect(url_for('main.managed_transactions_list'))


@main_bp.route('/transactions/edit/<int:item_id>', methods=['POST'])
@login_required
def managed_transactions_edit(item_id):
    row = ManagedTransaction.query.get_or_404(item_id)
    authority = request.form.get('authority') or row.authority
    service = request.form.get('service') or row.service
    description = request.form.get('description') if request.form.get('description') is not None else row.description
    status = request.form.get('status') or row.status
    fee_raw = request.form.get('fee')
    new_fee = row.fee
    if fee_raw is not None:
        try:
            fee_value = float((fee_raw or '').strip() or 0)
            if fee_value < 0:
                raise ValueError('negative fee')
            new_fee = fee_value
        except Exception:
            flash('قيمة الرسوم غير صحيحة', 'danger')
            return redirect(url_for('main.managed_transactions_list'))

    if authority not in AUTHORITIES or not service or status not in STATUSES:
        flash('بيانات غير صحيحة', 'danger')
        return redirect(url_for('main.managed_transactions_list'))

    row.authority = authority
    row.service = service.strip()
    row.description = (description or '').strip()
    row.status = status
    row.fee = new_fee
    db.session.commit()
    flash('تم تحديث المعاملة', 'success')
    return redirect(url_for('main.managed_transactions_list'))


@main_bp.route('/transactions/delete/<int:item_id>', methods=['POST'])
@login_required
def managed_transactions_delete(item_id):
    row = ManagedTransaction.query.get_or_404(item_id)
    db.session.delete(row)
    db.session.commit()
    flash('تم حذف المعاملة', 'success')
    return redirect(url_for('main.managed_transactions_list'))
