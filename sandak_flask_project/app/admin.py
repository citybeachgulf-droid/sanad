from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from app import db
from app.models import User, Client, Transaction, Payment, Ministry, Service, TransactionRecord
from functools import wraps


admin_bp = Blueprint('admin', __name__, template_folder='templates')


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role != 'admin':
            return redirect(url_for('admin.unauthorized'))
        return view_func(*args, **kwargs)
    return login_required(wrapper)


@admin_bp.app_errorhandler(403)
def forbidden(_e):
    return render_template('unauthorized.html'), 403


@admin_bp.route('/unauthorized')
def unauthorized():
    return render_template('unauthorized.html'), 403


@admin_bp.route('/')
@admin_required
def dashboard_redirect():
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    num_employees = User.query.filter(User.role != 'admin').count()
    num_clients = Client.query.count()
    num_transactions = db.session.query(TransactionRecord).count() + db.session.query(Transaction).count()
    total_payments = db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0)).scalar() or 0
    return render_template(
        'admin/dashboard.html',
        num_employees=num_employees,
        num_clients=num_clients,
        num_transactions=num_transactions,
        total_payments=total_payments,
    )


# APIs
@admin_bp.route('/api/stats')
@admin_required
def api_stats():
    num_employees = User.query.filter(User.role != 'admin').count()
    num_clients = Client.query.count()
    num_transactions = db.session.query(TransactionRecord).count() + db.session.query(Transaction).count()
    total_payments = float(db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0)).scalar() or 0)
    return jsonify({
        'employees': num_employees,
        'clients': num_clients,
        'transactions': num_transactions,
        'payments_total': total_payments,
    })


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
    return render_template('admin/employees.html', employees=employees)


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
            return render_template('admin/employee_form.html')
        if User.query.filter((User.username == name) | (User.email == email)).first():
            flash('اسم المستخدم أو البريد مستخدم سابقاً', 'danger')
            return render_template('admin/employee_form.html')
        user = User(username=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('تمت إضافة الموظف', 'success')
        return redirect(url_for('admin.employees_list'))
    return render_template('admin/employee_form.html')


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
        db.session.commit()
        flash('تم تحديث بيانات الموظف', 'success')
        return redirect(url_for('admin.employees_list'))
    return render_template('admin/employee_form.html', user=user)


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

