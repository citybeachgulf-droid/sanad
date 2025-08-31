from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import User, Transaction

manager_bp = Blueprint("manager", __name__)

def manager_required():
    return current_user.is_authenticated and current_user.role == "manager"

@manager_bp.before_request
def check_role():
    # منع الوصول لغير المدير
    if not (current_user.is_authenticated and current_user.role == "manager"):
        from flask import redirect
        return redirect(url_for("auth.login"))

@manager_bp.route("/")
@login_required
def dashboard():
    users = User.query.order_by(User.id.desc()).all()
    transactions = Transaction.query.order_by(Transaction.id.desc()).limit(10).all()
    return render_template("dashboard_manager.html", users=users, transactions=transactions)

@manager_bp.route("/users/create", methods=["POST"])
@login_required
def create_user():
    if not manager_required():
        return redirect(url_for("auth.login"))
    name = request.form.get("name", "")
    email = request.form.get("email", "").lower().strip()
    role = request.form.get("role", "employee")
    password = request.form.get("password", "123456")
    if not name or not email:
        flash("الاسم والبريد مطلوبان", "warning")
        return redirect(url_for("manager.dashboard"))
    if User.query.filter_by(email=email).first():
        flash("البريد مستخدم مسبقًا", "danger")
        return redirect(url_for("manager.dashboard"))
    u = User(name=name, email=email, role=role)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    flash("تم إنشاء المستخدم", "success")
    return redirect(url_for("manager.dashboard"))

@manager_bp.route("/transactions/status/<int:tid>", methods=["POST"])
@login_required
def update_transaction_status(tid):
    if not manager_required():
        return redirect(url_for("auth.login"))
    status = request.form.get("status", "pending")
    tr = Transaction.query.get_or_404(tid)
    tr.status = status
    db.session.commit()
    flash("تم تحديث الحالة", "success")
    return redirect(url_for("manager.dashboard"))
