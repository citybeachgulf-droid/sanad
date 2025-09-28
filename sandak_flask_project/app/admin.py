from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from app import db
from app.models import User, Client, Transaction, Payment, Ministry, Service, TransactionRecord, Task, Invoice, InvoicePayment
from functools import wraps


admin_bp = Blueprint('admin', __name__, template_folder='templates')


# Centralized permission options: (key, label)
PERMISSION_OPTIONS = [
    ('clients', 'إدارة العملاء'),
    ('transactions', 'إدارة المعاملات'),
    ('payments', 'إدارة المدفوعات'),
    ('reports', 'عرض التقارير'),
]


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role != 'admin':
            return redirect(url_for('admin.unauthorized'))
        return view_func(*args, **kwargs)
    return login_required(wrapper)


def permission_required(permission_key):
    """Optional decorator to protect views by granular permission.

    Admins are always allowed; otherwise the user must have the given permission.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role != 'admin' and not current_user.has_permission(permission_key):
                return redirect(url_for('admin.unauthorized'))
            return view_func(*args, **kwargs)
        return login_required(wrapper)
    return decorator

@admin_bp.app_errorhandler(403)
def forbidden(_e):
    return render_template('unauthorized.html'), 403


@admin_bp.route('/unauthorized')
def unauthorized():
    return render_template('unauthorized.html'), 403


@admin_bp.route('/')
@admin_required
def dashboard_redirect():
    # Unify admin and main dashboards: redirect to the single dashboard
    return redirect(url_for('main.dashboard'))


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    # Legacy path: redirect to unified dashboard
    return redirect(url_for('main.dashboard'))


# APIs
@admin_bp.route('/api/stats')
@admin_required
def api_stats():
    num_employees = User.query.filter(User.role != 'admin').count()
    num_clients = Client.query.count()
    num_transactions = db.session.query(TransactionRecord).count() + db.session.query(Transaction).count()
    total_payments = float(db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0)).scalar() or 0)
    # Performance metrics per employee
    from sqlalchemy import func
    perfs = []
    users = User.query.all()
    for u in users:
        total = db.session.query(func.count(Transaction.id)).filter(Transaction.assigned_to == u.id).scalar() or 0
        completed = db.session.query(func.count(Transaction.id)).filter(Transaction.assigned_to == u.id, Transaction.status == 'completed').scalar() or 0
        # avg cycle time (completed_at - created_at) in hours
        rows = db.session.query(Transaction.created_at, Transaction.completed_at).filter(Transaction.assigned_to == u.id, Transaction.completed_at.isnot(None)).all()
        hours = []
        for c_at, comp_at in rows:
            try:
                hours.append((comp_at - c_at).total_seconds() / 3600.0)
            except Exception:
                pass
        avg_hours = round(sum(hours)/len(hours), 2) if hours else 0.0
        overdue = db.session.query(func.count(Transaction.id)).filter(Transaction.assigned_to == u.id, Transaction.status != 'completed', Transaction.due_date.isnot(None), Transaction.due_date < func.now()).scalar() or 0
        perfs.append({'user': u.username, 'total': int(total), 'completed': int(completed), 'avg_hours': float(avg_hours), 'overdue': int(overdue)})

    return jsonify({
        'employees': num_employees,
        'clients': num_clients,
        'transactions': num_transactions,
        'payments_total': total_payments,
        'performance': perfs,
    })


@admin_bp.route('/api/financial_summary')
@admin_required
def api_financial_summary():
    from sqlalchemy import func
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    def sum_since(dt):
        return float(db.session.query(func.coalesce(func.sum(InvoicePayment.amount), 0)).filter(InvoicePayment.paid_at >= dt).scalar() or 0)

    daily = sum_since(day_ago)
    weekly = sum_since(week_ago)
    monthly = sum_since(month_ago)

    overdue_invoices = (
        db.session.query(Invoice)
        .filter(Invoice.status != 'paid')
        .filter(Invoice.due_date.isnot(None))
        .filter(Invoice.due_date < now)
        .count()
    )
    return jsonify({'daily_income': daily, 'weekly_income': weekly, 'monthly_income': monthly, 'overdue_invoices': int(overdue_invoices)})


@admin_bp.route('/api/transactions_by_ministry')
@admin_required
def api_transactions_by_ministry():
    rows = (
        db.session.query(Ministry.name, db.func.count(TransactionRecord.id))
        .outerjoin(TransactionRecord, TransactionRecord.ministry_id == Ministry.id)
        .group_by(Ministry.name)
        .order_by(Ministry.name)
        .all()
    )
    labels = [r[0] for r in rows]
    counts = [int(r[1]) for r in rows]
    return jsonify({'labels': labels, 'counts': counts})


# Employees management
@admin_bp.route('/employees')
@admin_required
def employees_list():
    employees = User.query.order_by(User.id.desc()).all()
    return render_template('admin/employees.html', employees=employees, permission_options=PERMISSION_OPTIONS)


@admin_bp.route('/employees/create', methods=['GET', 'POST'])
@admin_required
def employees_create():
    if request.method == 'POST':
        name = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role') or 'staff'
        if not name or not email or not password:
            flash('الرجاء تعبئة الحقول المطلوبة', 'warning')
            return render_template('admin/employee_form.html', permission_options=PERMISSION_OPTIONS)
        if User.query.filter((User.username == name) | (User.email == email)).first():
            flash('اسم المستخدم أو البريد مستخدم سابقاً', 'danger')
            return render_template('admin/employee_form.html', permission_options=PERMISSION_OPTIONS)
        user = User(username=name, email=email, role=role)
        user.set_password(password)
        # Collect permissions from form
        perms = {}
        for key, _label in PERMISSION_OPTIONS:
            perms[key] = bool(request.form.get(f'perm_{key}'))
        user.set_permissions(perms)
        db.session.add(user)
        db.session.commit()
        flash('تمت إضافة الموظف', 'success')
        return redirect(url_for('admin.employees_list'))
    return render_template('admin/employee_form.html', permission_options=PERMISSION_OPTIONS)


@admin_bp.route('/employees/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def employees_edit(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form.get('username') or user.username
        user.email = request.form.get('email') or user.email
        role = request.form.get('role')
        if role:
            user.role = role
        password = request.form.get('password')
        if password:
            user.set_password(password)
        # Update permissions from form
        perms = {}
        for key, _label in PERMISSION_OPTIONS:
            perms[key] = bool(request.form.get(f'perm_{key}'))
        user.set_permissions(perms)
        db.session.commit()
        flash('تم تحديث بيانات الموظف', 'success')
        return redirect(url_for('admin.employees_list'))
    return render_template('admin/employee_form.html', user=user, permission_options=PERMISSION_OPTIONS)


@admin_bp.route('/employees/<int:user_id>/delete', methods=['POST'])
@admin_required
def employees_delete(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('لا يمكنك حذف نفسك', 'danger')
        return redirect(url_for('admin.employees_list'))
    db.session.delete(user)
    db.session.commit()
    flash('تم حذف الموظف', 'success')
    return redirect(url_for('admin.employees_list'))


# Clients management
@admin_bp.route('/clients')
@admin_required
def clients_list():
    q = request.args.get('q', '').strip()
    query = Client.query
    if q:
        query = query.filter((Client.name.ilike(f'%{q}%')) | (Client.phone.ilike(f'%{q}%')))
    clients = query.order_by(Client.created_at.desc()).all()
    return render_template('admin/clients.html', clients=clients, q=q)


@admin_bp.route('/clients/create', methods=['GET', 'POST'])
@admin_required
def clients_create():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        national_id = request.form.get('national_id')
        if not name:
            flash('الاسم مطلوب', 'warning')
            return render_template('admin/client_form.html')
        c = Client(name=name, phone=phone, email=email, national_id=national_id)
        db.session.add(c)
        db.session.commit()
        flash('تم إضافة العميل', 'success')
        return redirect(url_for('admin.clients_list'))
    return render_template('admin/client_form.html')


# Transactions management
@admin_bp.route('/transactions')
@admin_required
def transactions_list():
    ministry_id = request.args.get('ministry_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    query = db.session.query(TransactionRecord)
    if ministry_id:
        query = query.filter(TransactionRecord.ministry_id == ministry_id)
    # date filters if provided
    if date_from:
        try:
            from datetime import datetime as dt
            query = query.filter(TransactionRecord.created_at >= dt.fromisoformat(date_from))
        except Exception:
            pass
    if date_to:
        try:
            from datetime import datetime as dt
            query = query.filter(TransactionRecord.created_at <= dt.fromisoformat(date_to))
        except Exception:
            pass

    records = query.order_by(TransactionRecord.created_at.desc()).all()
    ministries = Ministry.query.order_by(Ministry.name).all()
    return render_template('admin/transactions.html', records=records, ministries=ministries, ministry_id=ministry_id, date_from=date_from, date_to=date_to)


@admin_bp.route('/transactions/<int:record_id>')
@admin_required
def transaction_detail(record_id):
    rec = TransactionRecord.query.get_or_404(record_id)
    return render_template('admin/transaction_detail.html', rec=rec)


# Settings
@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    if request.method == 'POST':
        # update profile
        name = request.form.get('username')
        email = request.form.get('email')
        if name:
            current_user.username = name
        if email:
            current_user.email = email
        db.session.commit()
        flash('تم تحديث البيانات', 'success')
        return redirect(url_for('admin.settings'))
    return render_template('admin/settings.html')


@admin_bp.route('/settings/password', methods=['POST'])
@admin_required
def change_password():
    from werkzeug.security import check_password_hash
    current = request.form.get('current_password')
    new = request.form.get('new_password')
    confirm = request.form.get('confirm_password')
    if not new or new != confirm:
        flash('تأكيد كلمة المرور غير متطابق', 'danger')
        return redirect(url_for('admin.settings'))
    if not current_user.check_password(current):
        flash('كلمة المرور الحالية غير صحيحة', 'danger')
        return redirect(url_for('admin.settings'))
    current_user.set_password(new)
    db.session.commit()
    flash('تم تغيير كلمة المرور', 'success')
    return redirect(url_for('admin.settings'))

