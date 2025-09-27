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
def load_user(id):
    return User.query.get(int(id))


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
    status = db.Column(db.String(50), default='pending')
    fee = db.Column(db.Numeric(12,2), default=0)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    payments = db.relationship('Payment', backref='transaction', lazy=True)


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
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
