from flask import Flask
from .config import Config
from .extensions import init_extensions

# blueprints
from .blueprints.main import main_bp
from .blueprints.customers import customers_bp
from .blueprints.services import services_bp
from .blueprints.tickets import tickets_bp
from .blueprints.invoices import invoices_bp

def create_app():
    app = Flask(__name__, template_folder="templates")
    app.config.from_object(Config)

    init_extensions(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(customers_bp, url_prefix="/customers")
    app.register_blueprint(services_bp, url_prefix="/services")
    app.register_blueprint(tickets_bp, url_prefix="/tickets")
    app.register_blueprint(invoices_bp, url_prefix="/invoices")

    return app
