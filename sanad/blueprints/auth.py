from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from extensions import db
from models import User

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("تم تسجيل الدخول بنجاح", "success")
            # تحويل حسب الدور
            if user.role == "manager":
                return redirect(url_for("manager.dashboard"))
            elif user.role == "finance":
                return redirect(url_for("finance.dashboard"))
            else:
                return redirect(url_for("employees.dashboard"))
        flash("بيانات الدخول غير صحيحة", "danger")
    return render_template("login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("تم تسجيل الخروج", "info")
    return redirect(url_for("auth.login"))
