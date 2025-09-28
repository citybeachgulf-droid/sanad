from datetime import datetime
import json
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='staff')  # admin | staff
    permissions = db.Column(db.Text, default='{}', nullable=False)  # JSON string of granular permissions
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_permissions(self):
        """Return permissions as a dict. Admin implicitly has all permissions."""
        try:
            return json.loads(self.permissions or '{}')
        except Exception:
            return {}

    def set_permissions(self, permissions_dict):
        """Persist permissions dict as JSON string."""
        try:
            self.permissions = json.dumps(permissions_dict or {})
        except Exception:
            # Fallback to empty permissions on serialization error
            self.permissions = '{}'

    def has_permission(self, permission_key):
        """Check if user has a specific granular permission. Admin always true."""
        if self.role == 'admin':
            return True
        perms = self.get_permissions()
        return bool(perms.get(permission_key))


@login.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))



class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    national_id = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship('Transaction', backref='client', lazy=True)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    office = db.Column(db.String(100))
    service_type = db.Column(db.String(150))
    # new | in_progress | completed | overdue
    status = db.Column(db.String(50), default='new')
    fee = db.Column(db.Numeric(12,2), default=0)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Enhancements
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    delay_reason = db.Column(db.Text, nullable=True)

    payments = db.relationship('Payment', backref='transaction', lazy=True)
    assigned_user = db.relationship('User', foreign_keys=[assigned_to])


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'))
    amount = db.Column(db.Numeric(12,2))
    method = db.Column(db.String(50))
    reference = db.Column(db.String(120))
    paid_at = db.Column(db.DateTime, default=datetime.utcnow)


# New domain models for ministries/services and government transactions
class Ministry(db.Model):
    __tablename__ = 'ministries'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)

    services = db.relationship('Service', backref='ministry', lazy=True, cascade='all, delete-orphan')


class Service(db.Model):
    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True)
    ministry_id = db.Column(db.Integer, db.ForeignKey('ministries.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)


class TransactionRecord(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(200), nullable=False)
    client_phone = db.Column(db.String(50))
    ministry_id = db.Column(db.Integer, db.ForeignKey('ministries.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    ministry = db.relationship('Ministry')
    service = db.relationship('Service')
    employee = db.relationship('User')


class ManagedTransaction(db.Model):
    __tablename__ = 'managed_transactions'
    id = db.Column(db.Integer, primary_key=True)
    authority = db.Column(db.String(200), nullable=False)
    service = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    fee = db.Column(db.Numeric(12,2), nullable=False, default=0)
    status = db.Column(db.String(50), nullable=False, default='نشطة')
    is_paid = db.Column(db.Boolean, nullable=False, default=False)
    paid_amount = db.Column(db.Numeric(12,2), nullable=False, default=0)
    paid_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------- Additional domain models ----------------

class ClientContact(db.Model):
    __tablename__ = 'client_contacts'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    kind = db.Column(db.String(20), nullable=False)  # phone | email | whatsapp
    value = db.Column(db.String(200), nullable=False)
    is_primary = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ClientNote(db.Model):
    __tablename__ = 'client_notes'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(30), default='todo')  # todo | in_progress | done | blocked
    priority = db.Column(db.String(20), default='medium')  # low | medium | high
    due_date = db.Column(db.DateTime, nullable=True)
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=True)
    total_amount = db.Column(db.Numeric(12,2), nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default='unpaid')  # unpaid | partial | paid | overdue
    due_date = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InvoicePayment(db.Model):
    __tablename__ = 'invoice_payments'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    amount = db.Column(db.Numeric(12,2), nullable=False)
    method = db.Column(db.String(50))
    reference = db.Column(db.String(120))
    paid_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------- Income ledger ----------------

class Income(db.Model):
    __tablename__ = 'incomes'
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(50), nullable=False)  # e.g., managed_transaction, transaction, invoice
    source_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(12,2), nullable=False)
    method = db.Column(db.String(50))
    reference = db.Column(db.String(120))
    description = db.Column(db.Text)
    received_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def unique_key(self):
        return f"{self.source}:{self.source_id}"

