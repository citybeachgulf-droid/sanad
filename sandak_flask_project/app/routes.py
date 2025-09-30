# app/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.models import Transaction, ManagedTransaction, User, Income, Client


# ------------------- Main Blueprint -------------------
main_bp = Blueprint('main', __name__)

# تعيين url_prefix بشكل صريح لتفادي تعارضات مستقبلية مع المسارات
main_bp = Blueprint('main', __name__, url_prefix='')

# تعيين url_prefix بشكل صريح لتفادي تعارضات مستقبلية مع المسارات
main_bp = Blueprint('main', __name__, url_prefix='')


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    # بيانات افتراضية - استبدلها بالاستعلامات الحقيقية
    total_clients = Client.query.count()
    total_transactions = Transaction.query.count()
    in_progress_count = Transaction.query.filter_by(status='in_progress').count()
    overdue_count = Transaction.query.filter(Transaction.status!='completed', Transaction.due_date<datetime.utcnow()).count()
    now = datetime.utcnow()
    employees = User.query.order_by(User.username.asc()).all()
    items = Transaction.query.order_by(Transaction.created_at.desc()).limit(20).all()

    return render_template(
        'dashboard.html',
        total_clients=total_clients,
        total_transactions=total_transactions,
        in_progress_count=in_progress_count,
        overdue_count=overdue_count,
        employees=employees,
        now=now,
        items=items,
        status=None,
        employee_id=None,
        service_type=None
    )

# ------------------- Transactions Blueprint -------------------
transactions_bp = Blueprint('transactions', __name__, url_prefix='/transactions')

@transactions_bp.route('/')
@login_required
def list_transactions():
    status = request.args.get('status', '').strip()
    employee_id = request.args.get('employee_id', type=int)
    service_type = request.args.get('service_type', '').strip()

    q = Transaction.query
    if status:
        q = q.filter(Transaction.status == status)
    if employee_id:
        q = q.filter(Transaction.assigned_to == employee_id)
    if service_type:
        q = q.filter(Transaction.service_type.ilike(f"%{service_type}%"))

    items = q.order_by(Transaction.created_at.desc()).all()
    employees = User.query.order_by(User.username.asc()).all()
    return render_template('transactions/list.html', items=items, employees=employees,
                           status=status, employee_id=employee_id, service_type=service_type)

@transactions_bp.route('/new', methods=['GET','POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        client_id = request.form.get('client_id', type=int)
        service_type = request.form.get('service_type')
        notes = request.form.get('notes', '').strip()
        if not client_id or not service_type:
            flash('الرجاء تعبئة جميع الحقول المطلوبة', 'danger')
            return redirect(url_for('transactions.add_transaction'))

        tx = Transaction(
            client_id=client_id,
            service_type=service_type,
            notes=notes,
            status='new',
            assigned_to=None,
            created_by=current_user.id
        )
        db.session.add(tx)
        db.session.commit()
        flash('تم إضافة المعاملة بنجاح', 'success')
        return redirect(url_for('transactions.list_transactions'))

    return render_template('transactions/new.html')

@transactions_bp.route('/<int:id>/update-status', methods=['POST'])
@login_required
def update_transaction_status(id):
    tx = Transaction.query.get_or_404(id)
    if current_user.role != 'admin' and tx.created_by != current_user.id:
        flash('ليست لديك صلاحية لتعديل هذه المعاملة', 'danger')
        return redirect(url_for('transactions.list_transactions'))

    status = request.form.get('status', '').strip()
    amount = request.form.get('amount', type=float)

    if status not in ('in_progress', 'completed'):
        flash('حالة غير صالحة', 'danger')
        return redirect(url_for('transactions.list_transactions'))

    tx.status = status
    if status == 'completed' and amount:
        tx.paid_amount = amount
        tx.paid_at = datetime.utcnow()

    db.session.commit()
    flash('تم تحديث المعاملة', 'success')
    return redirect(url_for('transactions.list_transactions'))

@transactions_bp.route('/<int:id>/assign', methods=['POST'])
@login_required
def assign_transaction(id):
    if current_user.role != 'admin':
        flash('هذه العملية تتطلب صلاحية المشرف', 'danger')
        return redirect(url_for('transactions.list_transactions'))

    tx = Transaction.query.get_or_404(id)
    employee_id = request.form.get('employee_id', type=int)
    if not employee_id:
        flash('يرجى اختيار موظف', 'warning')
        return redirect(url_for('transactions.list_transactions'))

    tx.assigned_to = employee_id
    db.session.commit()
    flash('تم توكيل المعاملة لموظف آخر', 'success')
    return redirect(url_for('transactions.list_transactions'))

# ------------------- Catalog Blueprint -------------------
catalog_bp = Blueprint('catalog', __name__, url_prefix='/catalog')

AUTHORITIES = ['وزارة التجارة', 'وزارة العمل', 'شرطة عمان', 'وزارة الصحة']
STATUSES = ['نشطة', 'معلقة', 'منتهية']

@catalog_bp.route('/authorities')
@login_required
def list_authorities():
    return render_template('catalog/authorities.html', authorities=AUTHORITIES)

@catalog_bp.route('/authorities/<int:id>/services')
@login_required
def list_services(id):
    authority = AUTHORITIES[id] if 0 <= id < len(AUTHORITIES) else None
    if not authority:
        flash('جهة غير صالحة', 'danger')
        return redirect(url_for('catalog.list_authorities'))

    services = ManagedTransaction.query.filter_by(authority=authority).all()
    return render_template('catalog/services.html', authority=authority, services=services)

@catalog_bp.route('/service/add', methods=['POST'])
@login_required
def add_service():
    authority = request.form.get('authority')
    service_name = request.form.get('service')
    fee = request.form.get('fee', type=float)
    status = request.form.get('status', 'نشطة')
    if not authority or not service_name or fee is None or status not in STATUSES:
        flash('الرجاء تعبئة الحقول بشكل صحيح', 'danger')
        return redirect(url_for('catalog.list_authorities'))

    service = ManagedTransaction(authority=authority, service=service_name, fee=fee, status=status)
    db.session.add(service)
    db.session.commit()
    flash('تمت إضافة الخدمة', 'success')
    return redirect(url_for('catalog.list_services', id=AUTHORITIES.index(authority)))

@catalog_bp.route('/service/<int:id>/update', methods=['POST'])
@login_required
def update_service(id):
    service = ManagedTransaction.query.get_or_404(id)
    service.service = request.form.get('service', service.service)
    service.fee = request.form.get('fee', service.fee)
    service.status = request.form.get('status', service.status)
    db.session.commit()
    flash('تم تحديث الخدمة', 'success')
    return redirect(url_for('catalog.list_services', id=AUTHORITIES.index(service.authority)))

@catalog_bp.route('/service/<int:id>/delete', methods=['POST'])
@login_required
def delete_service(id):
    service = ManagedTransaction.query.get_or_404(id)
    db.session.delete(service)
    db.session.commit()
    flash('تم حذف الخدمة', 'success')
    return redirect(url_for('catalog.list_services', id=AUTHORITIES.index(service.authority)))
