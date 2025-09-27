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

    # Ensure critical columns exist when running without migrations (e.g., CI/containers)
    # Flask 3.0 removed before_first_request; perform this once at startup within app context.
    try:
        from sqlalchemy import text
        with app.app_context():
            with db.engine.connect() as conn:
                res = conn.execute(text("PRAGMA table_info(managed_transactions)")).fetchall()
                cols = {row[1] for row in res} if res else set()
                if 'fee' not in cols:
                    conn.execute(text("ALTER TABLE managed_transactions ADD COLUMN fee NUMERIC DEFAULT 0"))
    except Exception:
        # Silently skip to avoid breaking app startup in environments without SQLite PRAGMA
        pass

    # Blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    from app.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Admin blueprint
    try:
        from app.admin import admin_bp
        app.register_blueprint(admin_bp, url_prefix='/admin')
    except Exception:
        # Admin may not be present during early migrations/first run
        pass

    # CLI seed command
    @app.cli.command('seed')
    @with_appcontext
    def seed_command():
        """Seed initial ministries and services."""
        from app import db
        from app.models import Ministry, Service, User, ManagedTransaction

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

        # Seed managed transactions (authorities/services catalog)
        catalog = {
            'شرطة عمان السلطانية': [
                ('إصدار بطاقة الأحوال المدنية', 'إصدار بطاقة جديدة للمواطنين.'),
                ('تجديد بطاقة الأحوال المدنية', 'تجديد البطاقة عند انتهاء صلاحيتها.'),
                ('إصدار رخصة قيادة', 'إصدار رخصة قيادة جديدة.'),
                ('تجديد رخصة قيادة', 'تجديد رخصة القيادة المنتهية.'),
                ('نقل ملكية مركبة', 'تسجيل انتقال ملكية المركبات بين الأشخاص.'),
                ('دفع المخالفات المرورية', 'دفع الغرامات والمخالفات.'),
                ('إصدار بلاغ فقدان', 'تسجيل فقدان بطاقة شخصية أو رخصة أو جواز.'),
                ('خدمات التأشيرات والإقامة', 'استخراج وتجديد الإقامة للوافدين.'),
            ],
            'وزارة العمل': [
                ('إصدار تراخيص العمل', 'منح تصريح عمل جديد للعاملين.'),
                ('تجديد تراخيص العمل', 'تجديد تراخيص العمل المنتهية.'),
                ('تسجيل عقود العمل', 'تسجيل عقود العاملين.'),
                ('نقل الكفالة', 'تحويل كفالة العامل من جهة إلى أخرى.'),
                ('إنهاء خدمات العمالة', 'إنهاء عقد العمل للموظف أو العامل الوافد.'),
                ('طلبات استقدام العمالة', 'طلب إدخال عمالة جديدة.'),
            ],
            'وزارة التجارة والصناعة وترويج الاستثمار': [
                ('تسجيل المؤسسات الفردية', 'إنشاء سجل تجاري لمؤسسة فردية.'),
                ('تسجيل الشركات', 'إنشاء سجل تجاري لشركة جديدة.'),
                ('تجديد السجلات التجارية', 'تجديد السجل التجاري القائم.'),
                ('تعديل بيانات السجل التجاري', 'تحديث معلومات السجل التجاري.'),
            ],
            'الهيئة العامة للتأمينات الاجتماعية': [
                ('تسجيل موظفين جدد', 'إضافة موظفين لنظام التأمينات.'),
                ('تحديث بيانات المؤمن عليهم', 'تعديل معلومات الموظفين.'),
                ('استخراج شهادات الاشتراك', 'إصدار شهادات للمؤمن عليهم.'),
                ('استفسارات المستحقات والمعاشات', 'الاستعلام عن المعاشات.'),
            ],
            'وزارة الصحة': [
                ('إصدار وتجديد البطاقة الصحية للعاملين', None),
                ('تسجيل شهادات التطعيم', None),
                ('دفع رسوم بعض الخدمات الصحية', None),
            ],
            'وزارة الإسكان': [
                ('استخراج خرائط الأراضي', None),
                ('تحديث بيانات الملكية العقارية', None),
                ('متابعة طلبات المنح والإفراغات', None),
            ],
            'البلدية': [
                ('إصدار وتجديد التراخيص البلدية للمحلات', None),
                ('استخراج شهادات صحية للعمالة', None),
                ('دفع المخالفات البلدية', None),
            ],
            'هيئة الكهرباء والمياه والاتصالات': [
                ('دفع فواتير الكهرباء والمياه', None),
                ('الاستفسار عن الاشتراكات', None),
                ('طلبات توصيل جديدة', None),
            ],
            'هيئة الاتصالات وتقنية المعلومات': [
                ('دفع فواتير شركات الاتصالات (عمانتل، أوريدو)', None),
                ('إعادة شحن الرصيد', None),
                ('الاشتراك في بعض الخدمات الإلكترونية', None),
            ],
        }

        created = 0
        for auth, services in catalog.items():
            for svc, desc in services:
                exists = ManagedTransaction.query.filter_by(authority=auth, service=svc).first()
                if not exists:
                    db.session.add(ManagedTransaction(authority=auth, service=svc, description=desc or '', status='نشطة'))
                    created += 1
        if created:
            db.session.commit()
        click.echo(f'Seeded managed transactions: {created} added.')

    return app
