from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
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

@employees_bp.route("/transactions/history")
@login_required
def transactions_history():
    q = Transaction.query
    if current_user.role == "employee":
        q = q.filter_by(owner_id=current_user.id)
    pending_transactions = q.filter_by(status="pending").order_by(Transaction.id.desc()).all()
    completed_transactions = Transaction.query
    if current_user.role == "employee":
        completed_transactions = completed_transactions.filter_by(owner_id=current_user.id)
    completed_transactions = completed_transactions.filter_by(status="completed").order_by(Transaction.id.desc()).all()
    return render_template(
        "transactions_history.html",
        pending_transactions=pending_transactions,
        completed_transactions=completed_transactions,
    )

@employees_bp.route("/transactions/status/<int:tid>", methods=["POST"])
@login_required
def update_transaction_status(tid):
    new_status = request.form.get("status", "pending").strip()
    tr = Transaction.query.get_or_404(tid)
    # السماح للمدير/المالية أو مالك المعاملة فقط بالتعديل
    if not (current_user.role in ("manager", "finance") or tr.owner_id == current_user.id):
        flash("غير مصرح بتعديل هذه المعاملة", "danger")
        return redirect(url_for("employees.transactions_history"))
    tr.status = new_status
    db.session.commit()
    flash("تم تحديث الحالة", "success")
    return redirect(url_for("employees.transactions_history"))
