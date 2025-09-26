from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='staff')  # admin | staff

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


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
