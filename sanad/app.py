from flask import Flask, render_template, redirect, url_for
from flask_login import current_user
from config import Config
from extensions import db, login_manager

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    login_manager.init_app(app)

    # Import models to register with SQLAlchemy (after app and extensions are initialized)
    from models import User

    # Blueprints
    from blueprints.auth import auth_bp
    from blueprints.manager import manager_bp
    from blueprints.finance import finance_bp
    from blueprints.employees import employees_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(manager_bp, url_prefix="/manager")
    app.register_blueprint(finance_bp, url_prefix="/finance")
    app.register_blueprint(employees_bp, url_prefix="/employees")

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            if current_user.role == "manager":
                return redirect(url_for("manager.dashboard"))
            elif current_user.role == "finance":
                return redirect(url_for("finance.dashboard"))
            else:
                return redirect(url_for("employees.dashboard"))
        return render_template("index.html")

    return app

app = create_app()
