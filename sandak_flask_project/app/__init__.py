from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
from flask.cli import with_appcontext
import click

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)

    # Blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    from app.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # CLI seed command
    @app.cli.command('seed')
    @with_appcontext
    def seed_command():
        """Seed initial ministries and services."""
        from app import db
        from app.models import Ministry, Service, User

        db.create_all()

        # Create a default employee user if none exists
        if not User.query.filter_by(username='employee').first():
            u = User(username='employee', email='employee@example.com', role='staff')
            u.set_password('password')
            db.session.add(u)

        name_to_services = {
            'وزارة الإسكان والتخطيط العمراني': [
                'استخراج سند ملكية', 'نقل ملكية أرض/منزل', 'فرز أرض', 'رهن عقار', 'إصدار كشف مساحة'
            ],
            'وزارة العدل والشؤون القانونية': [
                'تصديق عقود البيع', 'الوكالات العامة والخاصة', 'فسخ العقود', 'توثيق الرهون'
            ],
            'وزارة العمل': [
                'تصريح استقدام عامل', 'تجديد عقد عمل', 'إلغاء تصريح عمل', 'تغيير جهة العمل'
            ],
            'شرطة عمان السلطانية': [
                'تجديد مركبة', 'نقل ملكية', 'استخراج رخصة قيادة', 'إصدار بطاقة', 'تجديد بطاقة', 'إصدار شهادة ميلاد/وفاة'
            ],
            'وزارة التجارة والصناعة وترويج الاستثمار': [
                'تسجيل مؤسسة جديدة', 'تجديد السجل التجاري', 'تعديل بيانات السجل', 'شطب سجل'
            ],
            'البلديات': [
                'تصريح بناء', 'شهادة إتمام بناء', 'تصريح نشاط تجاري', 'تراخيص صحية'
            ],
            'وزارة الصحة': [
                'تصاريح مهن صحية', 'تراخيص منشآت طبية', 'شهادات صحية'
            ],
            'وزارة التربية والتعليم': [
                'معادلة شهادات', 'تصديق شهادات دراسية'
            ],
            'الهيئة العامة لسجل القوى العاملة': [
                'تسجيل باحث عن عمل', 'تحديث بيانات'
            ],
        }

        for m_name, services in name_to_services.items():
            ministry = Ministry.query.filter_by(name=m_name).first()
            if not ministry:
                ministry = Ministry(name=m_name)
                db.session.add(ministry)
                db.session.flush()
            # Ensure services
            for s_name in services:
                if not Service.query.filter_by(ministry_id=ministry.id, name=s_name).first():
                    db.session.add(Service(ministry_id=ministry.id, name=s_name))

        db.session.commit()
        click.echo('Seeded ministries and services.')

    return app
