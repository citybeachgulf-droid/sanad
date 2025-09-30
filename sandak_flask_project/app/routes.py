# app/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_from_directory
from datetime import datetime, timedelta
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from flask import request
from app.forms import ClientForm
from app.models import TransactionRecord
from app.models import (
    Transaction, 
    ManagedTransaction, 
    User, 
    Income, 
    Client,
    ClientContact,
    ClientNote,
    Ministry,
    Service,
    Organization,
    OrgService
)


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
def clients():
    q = (request.args.get('q') or '').strip()
    clients_q = Client.query
    if q:
        clients_q = clients_q.filter(
            (Client.name.ilike(f"%{q}%")) | (Client.phone.ilike(f"%{q}%")) | (Client.email.ilike(f"%{q}%"))
        )
    clients = clients_q.order_by(Client.created_at.desc()).all()
    # Pull contacts and latest notes counts per client
    contacts_map = {}
    notes_count_map = {}
    if clients:
        client_ids = [c.id for c in clients]
        contact_rows = ClientContact.query.filter(ClientContact.client_id.in_(client_ids)).all()
        for r in contact_rows:
            contacts_map.setdefault(r.client_id, []).append(r)
        from sqlalchemy import func
        notes_rows = (
            db.session.query(ClientNote.client_id, func.count(ClientNote.id))
            .filter(ClientNote.client_id.in_(client_ids))
            .group_by(ClientNote.client_id)
            .all()
        )
        for cid, cnt in notes_rows:
            notes_count_map[cid] = int(cnt)
    return render_template('clients.html', clients=clients, contacts_map=contacts_map, notes_count_map=notes_count_map, q=q)


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


@main_bp.route('/clients/<int:client_id>')
@login_required
def client_detail(client_id):
    client = Client.query.get_or_404(client_id)
    # Filters for history
    date_from = (request.args.get('date_from') or '').strip()
    date_to = (request.args.get('date_to') or '').strip()
    tx_type = (request.args.get('tx_type') or '').strip()

    tx_q = Transaction.query.filter_by(client_id=client.id)
    if tx_type:
        tx_q = tx_q.filter(Transaction.service_type.ilike(f"%{tx_type}%"))
    from datetime import datetime as dt
    if date_from:
        try:
            tx_q = tx_q.filter(Transaction.created_at >= dt.fromisoformat(date_from))
        except Exception:
            pass
    if date_to:
        try:
            tx_q = tx_q.filter(Transaction.created_at <= dt.fromisoformat(date_to))
        except Exception:
            pass
    tx_items = tx_q.order_by(Transaction.created_at.desc()).all()

    contacts = ClientContact.query.filter_by(client_id=client.id).order_by(ClientContact.is_primary.desc(), ClientContact.id.desc()).all()
    notes = ClientNote.query.filter_by(client_id=client.id).order_by(ClientNote.created_at.desc()).all()
    return render_template('client_detail.html', client=client, contacts=contacts, notes=notes, tx_items=tx_items, date_from=date_from, date_to=date_to, tx_type=tx_type)


@main_bp.route('/clients/<int:client_id>/contacts/add', methods=['POST'])
@login_required
def client_add_contact(client_id):
    client = Client.query.get_or_404(client_id)
    kind = (request.form.get('kind') or 'phone').strip()
    value = (request.form.get('value') or '').strip()
    is_primary = bool(request.form.get('is_primary'))
    if not value:
        flash('قيمة وسيلة التواصل مطلوبة', 'warning')
        return redirect(url_for('main.client_detail', client_id=client.id))
    if is_primary:
        # unset others
        ClientContact.query.filter_by(client_id=client.id).update({ClientContact.is_primary: False})
    db.session.add(ClientContact(client_id=client.id, kind=kind, value=value, is_primary=is_primary))
    db.session.commit()
    flash('تمت إضافة وسيلة التواصل', 'success')
    return redirect(url_for('main.client_detail', client_id=client.id))


@main_bp.route('/clients/<int:client_id>/notes/add', methods=['POST'])
@login_required
def client_add_note(client_id):
    client = Client.query.get_or_404(client_id)
    content = (request.form.get('content') or '').strip()
    if not content:
        flash('الملاحظة مطلوبة', 'warning')
        return redirect(url_for('main.client_detail', client_id=client.id))
    db.session.add(ClientNote(client_id=client.id, content=content, created_by=current_user.id))
    db.session.commit()
    flash('تمت إضافة الملاحظة', 'success')
    return redirect(url_for('main.client_detail', client_id=client.id))


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

        # Upsert client into Clients page (save name and phone)
        client_row = None
        if client_phone:
            # Try to find by exact phone match first
            client_row = Client.query.filter(Client.phone == client_phone).first()
        if not client_row and client_name:
            # Fallback to name match if no phone match
            client_row = Client.query.filter(Client.name == client_name).first()
        if not client_row:
            client_row = Client(name=client_name, phone=client_phone or None)
            db.session.add(client_row)
            db.session.flush()
        else:
            # Update missing phone on existing client if provided
            if client_phone and not (client_row.phone and client_row.phone.strip()):
                client_row.phone = client_phone
                db.session.flush()

        # Ensure phone contact appears in Clients list badges
        if client_phone and client_row and client_row.id:
            exists_contact = (
                ClientContact.query
                .filter_by(client_id=client_row.id, kind='phone', value=client_phone)
                .first()
            )
            if not exists_contact:
                has_primary = ClientContact.query.filter_by(client_id=client_row.id, is_primary=True).first()
                db.session.add(ClientContact(
                    client_id=client_row.id,
                    kind='phone',
                    value=client_phone,
                    is_primary=False if has_primary else True,
                ))

        rec = TransactionRecord(
            client_name=client_name,
            client_phone=client_phone or None,
            ministry_id=int(ministry_id),
            service_id=int(service_id),
            notes=notes,
            employee_id=current_user.id,
        )
        # Prevent duplicate submissions within a short window
        from datetime import timedelta as _td
        cutoff = datetime.utcnow() - _td(minutes=2)
        existing = (
            TransactionRecord.query
            .filter(TransactionRecord.client_name == client_name)
            .filter(TransactionRecord.ministry_id == int(ministry_id))
            .filter(TransactionRecord.service_id == int(service_id))
            .filter(TransactionRecord.employee_id == current_user.id)
            .filter(TransactionRecord.created_at >= cutoff)
            .first()
        )
        if existing:
            flash('هذه المعاملة مسجلة بالفعل قبل قليل', 'warning')
            if current_user.role == 'admin':
                return redirect(url_for('admin.transactions_list'))
            return redirect(url_for('main.dashboard'))

        db.session.add(rec)
        db.session.commit()
        flash('تم حفظ المعاملة بنجاح', 'success')
        if current_user.role == 'admin':
            return redirect(url_for('admin.transactions_list'))
        return redirect(url_for('main.dashboard'))

    ministries = Ministry.query.order_by(Ministry.name).all()
    return render_template('add_transaction.html', ministries=ministries)


# Serve a basic service-worker to silence 404s in browsers expecting it
@main_bp.route('/service-worker.js')
def service_worker():
    try:
        # If a real static file exists, serve it
        static_dir = current_app.static_folder
        return send_from_directory(static_dir, 'service-worker.js')
    except Exception:
        # Fallback: serve a minimal no-op service worker
        from flask import Response
        content = "self.addEventListener('install',()=>self.skipWaiting());self.addEventListener('activate',event=>event.waitUntil(clients.claim()));self.addEventListener('fetch',()=>{});"
        return Response(content, mimetype='application/javascript')


# Services API for dependent dropdown
@main_bp.route('/api/services')
@login_required
def api_services_by_ministry():
    ministry_id = request.args.get('ministry_id', type=int)
    if not ministry_id:
        return jsonify([])
    items = Service.query.filter_by(ministry_id=ministry_id).order_by(Service.name).all()
    return jsonify([{'id': s.id, 'name': s.name} for s in items])


# Catalog APIs
@main_bp.route('/api/organizations')
@login_required
def api_organizations():
    kind = request.args.get('kind')
    q = (request.args.get('q') or '').strip()
    query = Organization.query
    if kind:
        query = query.filter(Organization.kind == kind)
    if q:
        query = query.filter(Organization.name.ilike(f"%{q}%"))
    orgs = query.order_by(Organization.name.asc()).all()
    return jsonify([
        {'id': o.id, 'name': o.name, 'kind': o.kind} for o in orgs
    ])


@main_bp.route('/api/organizations/<int:org_id>/services')
@login_required
def api_org_services(org_id):
    only_active = request.args.get('only_active') in ('1', 'true', 'on')
    q = (request.args.get('q') or '').strip()
    query = OrgService.query.filter_by(organization_id=org_id)
    if only_active:
        query = query.filter(OrgService.is_active == True)
    if q:
        query = query.filter(OrgService.name.ilike(f"%{q}%"))
    items = query.order_by(OrgService.name.asc()).all()
    return jsonify([
        {'id': s.id, 'name': s.name, 'description': s.description, 'is_active': bool(s.is_active)} for s in items
    ])


# ----------------------- New Transactions Page (status == 'new') -----------------------

@main_bp.route('/transactions/new-items')
@login_required
def transactions_new():
    now = datetime.utcnow()
    employee_id = request.args.get('employee_id', type=int)
    service_type = request.args.get('service_type', '').strip()
    status = request.args.get('status')         # أو request.form.get('status') إذا كانت من POST
    employee_id = request.args.get('employee_id')
    service_type = request.args.get('service_type')

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





@main_bp.route('/clients')
def clients():
    clients_list = Client.query.all()
    return render_template('clients/list.html', clients=clients_list)
