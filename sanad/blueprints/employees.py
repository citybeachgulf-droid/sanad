from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from models import Transaction

employees_bp = Blueprint("employees", __name__)

@employees_bp.before_request
def check_role():
    if not current_user.is_authenticated:
        from flask import redirect
        return redirect(url_for("auth.login"))
    # يسمح للموظف والمدير والمالية بالدخول، لكن العرض يختلف
    return None

@employees_bp.route("/")
@login_required
def dashboard():
    q = Transaction.query
    if current_user.role == "employee":
        q = q.filter_by(owner_id=current_user.id)
    transactions = q.order_by(Transaction.id.desc()).all()
    return render_template("dashboard_employee.html", transactions=transactions)

@employees_bp.route("/transactions/create", methods=["POST"])
@login_required
def create_transaction():
    title = request.form.get("title", "").strip()
    amount = float(request.form.get("amount", "0") or 0)
    if not title:
        flash("عنوان المعاملة مطلوب", "warning")
        return redirect(url_for("employees.dashboard"))
    t = Transaction(title=title, amount=amount, owner_id=current_user.id)
    db.session.add(t)
    db.session.commit()
    flash("تم إنشاء المعاملة", "success")
    return redirect(url_for("employees.dashboard"))
