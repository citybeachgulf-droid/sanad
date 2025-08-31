from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import Expense, Transaction

finance_bp = Blueprint("finance", __name__)

@finance_bp.before_request
def check_role():
    if not (current_user.is_authenticated and current_user.role in ("finance", "manager")):
        from flask import redirect
        return redirect(url_for("auth.login"))

@finance_bp.route("/")
@login_required
def dashboard():
    expenses = Expense.query.order_by(Expense.id.desc()).all()
    # إجمالي مبالغ المعاملات (كمثال إيرادات)
    total_revenue = db.session.query(db.func.coalesce(db.func.sum(Transaction.amount), 0.0)).scalar()
    total_expense = db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0.0)).scalar()
    balance = (total_revenue or 0) - (total_expense or 0)
    return render_template("dashboard_finance.html", expenses=expenses, total_revenue=total_revenue or 0, total_expense=total_expense or 0, balance=balance)

@finance_bp.route("/expenses/create", methods=["POST"])
@login_required
def create_expense():
    desc = request.form.get("description", "").strip()
    amount = float(request.form.get("amount", "0") or 0)
    if not desc or amount <= 0:
        flash("البيانات غير مكتملة", "warning")
        return redirect(url_for("finance.dashboard"))
    e = Expense(description=desc, amount=amount, created_by_id=current_user.id)
    db.session.add(e)
    db.session.commit()
    flash("تم إضافة المصروف", "success")
    return redirect(url_for("finance.dashboard"))
