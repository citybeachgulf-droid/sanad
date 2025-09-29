from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from datetime import datetime, timedelta
from flask_login import login_required, current_user
from app import db
from app.models import User, Client, Transaction, Payment, Ministry, Service, TransactionRecord, ManagedTransaction, ClientContact, ClientNote, Task, Invoice, InvoicePayment, Income
from app.forms import ClientForm

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    # KPIs
    total_clients = Client.query.count()
    # Include both standard transactions and government transaction records
    total_transactions = Transaction.query.count() + TransactionRecord.query.count()

    # Status counts
    now = datetime.utcnow()
    new_count = Transaction.query.filter_by(status='new').count()
    in_progress_count = Transaction.query.filter_by(status='in_progress').count()
    completed_count = Transaction.query.filter_by(status='completed').count()
    overdue_count = (
        Transaction.query
        .filter(Transaction.status != 'completed')
        .filter(Transaction.due_date.isnot(None))
        .filter(Transaction.due_date < now)
        .count()
    )

    # Filters
    status = (request.args.get('status') or '').strip()
    employee_id = request.args.get('employee_id', type=int)
    service_type = (request.args.get('service_type') or '').strip()

    q = Transaction.query
    if status:
        if status == 'overdue':
            q = (
                q.filter(Transaction.status != 'completed')
                 .filter(Transaction.due_date.isnot(None))
                 .filter(Transaction.due_date < now)
            )
        else:
            q = q.filter(Transaction.status == status)
    if employee_id:
        q = q.filter(Transaction.assigned_to == employee_id)
    if service_type:
        q = q.filter(Transaction.service_type.ilike(f"%{service_type}%"))

    items = q.order_by(Transaction.created_at.desc()).limit(100).all()

    # Near deadlines (within 24h) for alerts
    near_deadline = (
        Transaction.query
        .filter(Transaction.status != 'completed')
        .filter(Transaction.due_date.isnot(None))
        .filter(Transaction.due_date >= now)
        .filter(Transaction.due_date <= now + timedelta(days=1))
        .order_by(Transaction.due_date.asc())
        .limit(10)
        .all()
    )

    employees = User.query.order_by(User.username.asc()).all()

    return render_template(
        'dashboard.html',
        total_clients=total_clients,
        total_transactions=total_transactions,
        pending=in_progress_count,  # kept for backward compat in template cards
        new_count=new_count,
        in_progress_count=in_progress_count,
        completed_count=completed_count,
        overdue_count=overdue_count,
        items=items,
        employees=employees,
        status=status,
        employee_id=employee_id,
        service_type=service_type,
        near_deadline=near_deadline,
        now=now,
    )


@main_bp.route('/clients')
@login_required
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
        db.session.add(rec)
        # Also create a standard Transaction entry so it appears in the "new" list
        try:
            m = Ministry.query.get(int(ministry_id)) if ministry_id else None
            s_obj = Service.query.get(int(service_id)) if service_id else None
        except Exception:
            m = None
            s_obj = None

        std_tx = Transaction(
            client_id=client_row.id if client_row and client_row.id else None,
            service_type=(s_obj.name if s_obj else None),
            office=(m.name if m else None),
            fee=0,
            details=notes,
        )
        db.session.add(std_tx)
        db.session.commit()
        flash('تم حفظ المعاملة بنجاح', 'success')
        return redirect(url_for('main.transactions_new'))

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


# ----------------------- New Transactions Page (status == 'new') -----------------------

@main_bp.route('/transactions/new-items')
@login_required
def transactions_new():
    now = datetime.utcnow()
    employee_id = request.args.get('employee_id', type=int)
    service_type = (request.args.get('service_type') or '').strip()

    q = Transaction.query.filter(Transaction.status == 'new')
    if employee_id:
        q = q.filter(Transaction.assigned_to == employee_id)
    if service_type:
        q = q.filter(Transaction.service_type.ilike(f"%{service_type}%"))

    items = q.order_by(Transaction.created_at.desc()).all()
    employees = User.query.order_by(User.username.asc()).all()
    return render_template(
        'transactions_new.html',
        items=items,
        employees=employees,
        employee_id=employee_id,
        service_type=service_type,
        now=now,
    )


# ----------------------- Managed Transactions (Authority/Service catalog) -----------------------

AUTHORITIES = [
    'وزارة الإسكان والتخطيط العمراني',
    'وزارة العدل والشؤون القانونية',
    'وزارة العمل',
    'شرطة عمان السلطانية',
    'وزارة التجارة والصناعة وترويج الاستثمار',
    'البلديات',
    'وزارة الصحة',
    'وزارة التربية والتعليم',
    'الهيئة العامة لسجل القوى العاملة',
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
    is_paid_raw = request.form.get('is_paid')
    paid_amount_raw = (request.form.get('paid_amount') or '').strip()
    try:
        fee_value = float(fee_raw) if fee_raw != '' else 0.0
        if fee_value < 0:
            raise ValueError('negative fee')
    except Exception:
        flash('قيمة الرسوم غير صحيحة', 'danger')
        return redirect(url_for('main.managed_transactions_list'))

    is_paid = bool(is_paid_raw)
    paid_amount = 0.0
    if is_paid:
        try:
            paid_amount = float(paid_amount_raw) if paid_amount_raw != '' else fee_value
            if paid_amount < 0:
                raise ValueError('negative paid amount')
        except Exception:
            flash('قيمة المبلغ المدفوع غير صحيحة', 'danger')
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
        is_paid=is_paid,
        paid_amount=paid_amount if is_paid else 0,
        paid_at=datetime.utcnow() if is_paid else None,
    )
    db.session.add(row)
    db.session.commit()
    flash('تمت إضافة المعاملة', 'success')
    return redirect(url_for('main.managed_transactions_list'))


# ---------------- Transactions helpers: update status and delay reason ----------------

@main_bp.route('/transactions/<int:transaction_id>/status', methods=['POST'])
@login_required
def update_transaction_status(transaction_id):
    row = Transaction.query.get_or_404(transaction_id)
    # simple permission: staff can modify their assigned or admins
    if current_user.role != 'admin' and row.assigned_to not in (None, current_user.id):
        flash('ليست لديك صلاحية لتعديل هذه المعاملة', 'danger')
        return redirect(url_for('main.dashboard'))

    status = (request.form.get('status') or '').strip()
    if status not in ('new', 'in_progress', 'completed'):
        flash('حالة غير صالحة', 'danger')
        return redirect(url_for('main.dashboard'))

    # Optionally update assignment and due date
    assigned_to = request.form.get('assigned_to', type=int)
    due_date_raw = (request.form.get('due_date') or '').strip()
    if assigned_to:
        row.assigned_to = assigned_to
    if due_date_raw:
        try:
            row.due_date = datetime.fromisoformat(due_date_raw)
        except Exception:
            flash('تاريخ الاستحقاق غير صالح', 'warning')

    # timestamps
    if status == 'in_progress' and row.started_at is None:
        row.started_at = datetime.utcnow()
    if status == 'completed' and row.completed_at is None:
        row.completed_at = datetime.utcnow()

    row.status = status
    db.session.commit()
    flash('تم تحديث حالة المعاملة', 'success')
    return redirect(url_for('main.dashboard'))


@main_bp.route('/transactions/<int:transaction_id>/delay', methods=['POST'])
@login_required
def set_transaction_delay_reason(transaction_id):
    row = Transaction.query.get_or_404(transaction_id)
    reason = (request.form.get('delay_reason') or '').strip()
    if not reason:
        flash('يرجى إدخال سبب التأخير', 'warning')
        return redirect(url_for('main.dashboard'))
    row.delay_reason = reason
    db.session.commit()
    flash('تم تسجيل سبب التأخير', 'success')
    return redirect(url_for('main.dashboard'))


# ---------------- Tasks: assign and update ----------------
@main_bp.route('/tasks/create', methods=['POST'])
@login_required
def tasks_create():
    title = (request.form.get('title') or '').strip()
    description = (request.form.get('description') or '').strip()
    assignee_id = request.form.get('assignee_id', type=int)
    priority = (request.form.get('priority') or 'medium').strip()
    due_date_raw = (request.form.get('due_date') or '').strip()
    transaction_id = request.form.get('transaction_id', type=int)
    client_id = request.form.get('client_id', type=int)
    if not title:
        flash('العنوان مطلوب', 'warning')
        return redirect(url_for('main.dashboard'))
    due_date = None
    if due_date_raw:
        try:
            due_date = datetime.fromisoformat(due_date_raw)
        except Exception:
            pass
    row = Task(title=title, description=description, assignee_id=assignee_id, priority=priority, due_date=due_date, transaction_id=transaction_id, client_id=client_id, creator_id=current_user.id)
    db.session.add(row)
    db.session.commit()
    flash('تم إنشاء المهمة', 'success')
    return redirect(url_for('main.dashboard'))


@main_bp.route('/tasks/<int:task_id>/status', methods=['POST'])
@login_required
def tasks_update_status(task_id):
    row = Task.query.get_or_404(task_id)
    status = (request.form.get('status') or '').strip()
    if status not in ('todo', 'in_progress', 'done', 'blocked'):
        flash('حالة غير صالحة', 'danger')
        return redirect(url_for('main.dashboard'))
    row.status = status
    db.session.commit()
    flash('تم تحديث حالة المهمة', 'success')
    return redirect(url_for('main.dashboard'))


# ---------------- Reports and Notifications ----------------

@main_bp.route('/reports/custom')
@login_required
def custom_reports():
    # Filters
    employee_id = request.args.get('employee_id', type=int)
    client_id = request.args.get('client_id', type=int)
    date_from = (request.args.get('date_from') or '').strip()
    date_to = (request.args.get('date_to') or '').strip()
    tx_status = (request.args.get('tx_status') or '').strip()

    q = Transaction.query
    if employee_id:
        q = q.filter(Transaction.assigned_to == employee_id)
    if client_id:
        q = q.filter(Transaction.client_id == client_id)
    if tx_status:
        q = q.filter(Transaction.status == tx_status)

    from datetime import datetime as dt
    if date_from:
        try:
            q = q.filter(Transaction.created_at >= dt.fromisoformat(date_from))
        except Exception:
            pass
    if date_to:
        try:
            q = q.filter(Transaction.created_at <= dt.fromisoformat(date_to))
        except Exception:
            pass

    items = q.order_by(Transaction.created_at.desc()).limit(500).all()
    employees = User.query.order_by(User.username.asc()).all()
    clients = Client.query.order_by(Client.name.asc()).all()
    return render_template('admin/custom_reports.html', items=items, employees=employees, clients=clients, employee_id=employee_id, client_id=client_id, date_from=date_from, date_to=date_to, tx_status=tx_status)


def send_email_stub(to_email: str, subject: str, body: str):
    # Placeholder for real SMTP integration
    print(f"EMAIL -> {to_email} | {subject}: {body}")


def send_whatsapp_stub(phone: str, body: str):
    # Placeholder for real WhatsApp API
    print(f"WHATSAPP -> {phone}: {body}")


@main_bp.route('/notifications/due_soon', methods=['POST'])
@login_required
def notify_due_soon():
    now = datetime.utcnow()
    soon = now + timedelta(days=1)
    items = (
        Transaction.query
        .filter(Transaction.status != 'completed')
        .filter(Transaction.due_date.isnot(None))
        .filter(Transaction.due_date >= now)
        .filter(Transaction.due_date <= soon)
        .all()
    )
    count = 0
    for t in items:
        # notify client via email/whatsapp if available
        if t.client and t.client.email:
            send_email_stub(t.client.email, 'تذكير موعد معاملة', f'معاملتك {t.service_type} ستستحق بتاريخ {t.due_date}')
            count += 1
        if t.client and t.client.phone:
            send_whatsapp_stub(t.client.phone, f'تذكير: معاملتك {t.service_type} تستحق {t.due_date}')
            count += 1
    flash(f'تم إرسال {count} تنبيه/تنبيهات', 'success')
    return redirect(url_for('main.dashboard'))


# ---------------- Invoices: CRUD and partial payments ----------------

@main_bp.route('/invoices')
@login_required
def invoices_list():
    client_id = request.args.get('client_id', type=int)
    status = (request.args.get('status') or '').strip()
    q = Invoice.query
    if client_id:
        q = q.filter(Invoice.client_id == client_id)
    if status:
        q = q.filter(Invoice.status == status)
    items = q.order_by(Invoice.created_at.desc()).all()
    clients = Client.query.order_by(Client.name.asc()).all()
    return render_template('admin/invoices.html', items=items, clients=clients, client_id=client_id, status=status)


@main_bp.route('/invoices/create', methods=['POST'])
@login_required
def invoices_create():
    client_id = request.form.get('client_id', type=int)
    total_amount = request.form.get('total_amount', type=float) or 0.0
    due_date_raw = (request.form.get('due_date') or '').strip()
    notes = (request.form.get('notes') or '').strip()
    if not client_id:
        flash('العميل مطلوب', 'warning')
        return redirect(url_for('main.invoices_list'))
    due_date = None
    if due_date_raw:
        try:
            due_date = datetime.fromisoformat(due_date_raw)
        except Exception:
            pass
    inv = Invoice(client_id=client_id, total_amount=total_amount, due_date=due_date, notes=notes)
    db.session.add(inv)
    db.session.commit()
    flash('تم إنشاء الفاتورة', 'success')
    return redirect(url_for('main.invoices_list'))


@main_bp.route('/invoices/<int:invoice_id>')
@login_required
def invoice_detail(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    payments = InvoicePayment.query.filter_by(invoice_id=invoice_id).order_by(InvoicePayment.paid_at.desc()).all()
    clients = Client.query.order_by(Client.name.asc()).all()
    return render_template('admin/invoice_detail.html', inv=inv, payments=payments, clients=clients)


@main_bp.route('/invoices/<int:invoice_id>/pay', methods=['POST'])
@login_required
def invoice_add_payment(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    amount = request.form.get('amount', type=float)
    method = (request.form.get('method') or '').strip()
    reference = (request.form.get('reference') or '').strip()
    if not amount or amount <= 0:
        flash('المبلغ غير صالح', 'danger')
        return redirect(url_for('main.invoice_detail', invoice_id=invoice_id))
    pay = InvoicePayment(invoice_id=invoice_id, amount=amount, method=method, reference=reference)
    db.session.add(pay)
    # Update invoice status
    from sqlalchemy import func
    total_paid = (db.session.query(func.coalesce(func.sum(InvoicePayment.amount), 0)).filter(InvoicePayment.invoice_id == invoice_id).scalar() or 0) + amount
    if total_paid >= float(inv.total_amount or 0):
        inv.status = 'paid'
    elif total_paid > 0:
        inv.status = 'partial'
    db.session.commit()
    flash('تم تسجيل الدفعة', 'success')
    return redirect(url_for('main.invoice_detail', invoice_id=invoice_id))


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
    is_paid_raw = request.form.get('is_paid')
    paid_amount_raw = request.form.get('paid_amount')
    if fee_raw is not None:
        try:
            fee_value = float((fee_raw or '').strip() or 0)
            if fee_value < 0:
                raise ValueError('negative fee')
            new_fee = fee_value
        except Exception:
            flash('قيمة الرسوم غير صحيحة', 'danger')
            return redirect(url_for('main.managed_transactions_list'))

    # Payment handling
    new_is_paid = row.is_paid
    new_paid_amount = row.paid_amount
    new_paid_at = row.paid_at
    if is_paid_raw is not None:
        new_is_paid = True if is_paid_raw in ('on', 'true', '1') else False
    if paid_amount_raw is not None:
        try:
            value = float((paid_amount_raw or '').strip() or 0)
            if value < 0:
                raise ValueError('negative paid amount')
            new_paid_amount = value
        except Exception:
            flash('قيمة المبلغ المدفوع غير صحيحة', 'danger')
            return redirect(url_for('main.managed_transactions_list'))
    # Set paid_at when moving to paid, clear when unpaying
    if new_is_paid and not row.is_paid:
        new_paid_at = datetime.utcnow()
    if not new_is_paid:
        new_paid_at = None

    if authority not in AUTHORITIES or not service or status not in STATUSES:
        flash('بيانات غير صحيحة', 'danger')
        return redirect(url_for('main.managed_transactions_list'))

    row.authority = authority
    row.service = service.strip()
    row.description = (description or '').strip()
    row.status = status
    row.fee = new_fee
    row.is_paid = new_is_paid
    row.paid_amount = new_paid_amount if new_is_paid else 0
    row.paid_at = new_paid_at
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


# ---------------- Managed Transactions: fee collection -> record income ----------------

@main_bp.route('/transactions/<int:item_id>/collect', methods=['POST'])
@login_required
def managed_transactions_collect(item_id):
    row = ManagedTransaction.query.get_or_404(item_id)
    # Only allow collection when status is completed (منتهية)
    if row.status != 'منتهية':
        flash('لا يمكن التحصيل إلا بعد إنهاء المعاملة', 'warning')
        return redirect(url_for('main.managed_transactions_list'))

    amount = request.form.get('amount', type=float)
    method = (request.form.get('method') or '').strip()
    reference = (request.form.get('reference') or '').strip()
    description = f"{row.authority} - {row.service}"

    if amount is None or amount <= 0:
        # Default to fee if not provided or invalid
        try:
            amount = float(row.fee or 0)
        except Exception:
            amount = 0.0
    if amount <= 0:
        flash('المبلغ غير صالح للتحصيل', 'danger')
        return redirect(url_for('main.managed_transactions_list'))

    # Permission: admin only for now
    if current_user.role != 'admin':
        flash('هذه العملية تتطلب صلاحية المشرف', 'danger')
        return redirect(url_for('main.managed_transactions_list'))

    # Prevent duplicate income entries
    existing_income = Income.query.filter_by(source='managed_transaction', source_id=row.id).first()
    if existing_income:
        # Update amount/method/reference if needed
        existing_income.amount = amount
        existing_income.method = method or existing_income.method
        existing_income.reference = reference or existing_income.reference
        existing_income.description = description
        existing_income.received_at = datetime.utcnow()
    else:
        db.session.add(Income(
            source='managed_transaction',
            source_id=row.id,
            amount=amount,
            method=method,
            reference=reference,
            description=description,
        ))

    # Update managed transaction payment flags
    row.is_paid = True
    row.paid_amount = amount
    row.paid_at = datetime.utcnow()

    db.session.commit()
    flash('تم تحصيل الرسوم وتسجيلها كدخل', 'success')
    return redirect(url_for('main.managed_transactions_list'))
