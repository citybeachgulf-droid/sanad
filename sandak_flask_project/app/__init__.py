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

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)

    # ---------------- Schema compatibility ----------------
    def ensure_schema_compatibility():
        try:
            from sqlalchemy import text
            with db.engine.connect() as conn:
                # managed_transactions
                res = conn.execute(text("PRAGMA table_info(managed_transactions)")).fetchall()
                cols = {row[1] for row in res} if res else set()
                if 'fee' not in cols:
                    conn.execute(text("ALTER TABLE managed_transactions ADD COLUMN fee NUMERIC DEFAULT 0"))
                if 'is_paid' not in cols:
                    conn.execute(text("ALTER TABLE managed_transactions ADD COLUMN is_paid BOOLEAN DEFAULT 0"))
                if 'paid_amount' not in cols:
                    conn.execute(text("ALTER TABLE managed_transactions ADD COLUMN paid_amount NUMERIC DEFAULT 0"))
                if 'paid_at' not in cols:
                    conn.execute(text("ALTER TABLE managed_transactions ADD COLUMN paid_at DATETIME"))

                # transactions (TransactionRecord)
                res_tr = conn.execute(text("PRAGMA table_info(transactions)")).fetchall()
                tr_cols = {row[1] for row in res_tr} if res_tr else set()
                if 'client_phone' not in tr_cols:
                    conn.execute(text("ALTER TABLE transactions ADD COLUMN client_phone VARCHAR(50)"))

                # transaction enhancements
                res_tr2 = conn.execute(text("PRAGMA table_info(transaction)")).fetchall()
                tr2_cols = {row[1] for row in res_tr2} if res_tr2 else set()
                if 'assigned_to' not in tr2_cols:
                    conn.execute(text("ALTER TABLE transaction ADD COLUMN assigned_to INTEGER"))
                if 'due_date' not in tr2_cols:
                    conn.execute(text("ALTER TABLE transaction ADD COLUMN due_date DATETIME"))
                if 'started_at' not in tr2_cols:
                    conn.execute(text("ALTER TABLE transaction ADD COLUMN started_at DATETIME"))
                if 'completed_at' not in tr2_cols:
                    conn.execute(text("ALTER TABLE transaction ADD COLUMN completed_at DATETIME"))
                if 'delay_reason' not in tr2_cols:
                    conn.execute(text("ALTER TABLE transaction ADD COLUMN delay_reason TEXT"))
                if 'status' not in tr2_cols:
                    conn.execute(text("ALTER TABLE transaction ADD COLUMN status VARCHAR(50) DEFAULT 'new'"))

                # Create new tables if not exists
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS client_contacts (
                        id INTEGER PRIMARY KEY, client_id INTEGER NOT NULL,
                        kind VARCHAR(20) NOT NULL, value VARCHAR(200) NOT NULL,
                        is_primary BOOLEAN DEFAULT 0, created_at DATETIME
                    )
                """))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS client_notes (
                        id INTEGER PRIMARY KEY, client_id INTEGER NOT NULL,
                        content TEXT NOT NULL, created_by INTEGER, created_at DATETIME
                    )
                """))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY, title VARCHAR(200) NOT NULL,
                        description TEXT, status VARCHAR(30) DEFAULT 'todo',
                        priority VARCHAR(20) DEFAULT 'medium',
                        due_date DATETIME, assignee_id INTEGER, creator_id INTEGER,
                        transaction_id INTEGER, client_id INTEGER,
                        created_at DATETIME, updated_at DATETIME
                    )
                """))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS invoices (
                        id INTEGER PRIMARY KEY, client_id INTEGER NOT NULL,
                        transaction_id INTEGER, total_amount NUMERIC DEFAULT 0,
                        status VARCHAR(20) DEFAULT 'unpaid', due_date DATETIME,
                        notes TEXT, created_at DATETIME, updated_at DATETIME
                    )
                """))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS invoice_payments (
                        id INTEGER PRIMARY KEY, invoice_id INTEGER NOT NULL,
                        amount NUMERIC NOT NULL, method VARCHAR(50),
                        reference VARCHAR(120), paid_at DATETIME
                    )
                """))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS incomes (
                        id INTEGER PRIMARY KEY,
                        source VARCHAR(50) NOT NULL,
                        source_id INTEGER NOT NULL,
                        amount NUMERIC NOT NULL,
                        method VARCHAR(50),
                        reference VARCHAR(120),
                        description TEXT,
                        received_at DATETIME,
                        created_at DATETIME
                    )
                """))
        except Exception:
            pass

    # Ensure tables exist at app startup
    with app.app_context():
        ensure_schema_compatibility()
        db.create_all()

    # ---------------- Blueprints ----------------
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    from app.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    try:
        from app.admin import admin_bp
        app.register_blueprint(admin_bp, url_prefix='/admin')
    except ImportError:
        pass

    # ---------------- CLI Seed Command ----------------
    @app.cli.command('seed')
    @with_appcontext
    def seed_command():
        """Seed ministries, services, users, managed transactions."""
        from app.models import Ministry, Service, User, ManagedTransaction

        db.create_all()

        # Create default employee if missing
        if not User.query.filter_by(username='employee').first():
            u = User(username='employee', email='employee@example.com', role='staff')
            u.set_password('password')
            db.session.add(u)

        # Ministries & services
        name_to_services = {
            'وزارة الإسكان والتخطيط العمراني': [
                'استخراج سند ملكية','نقل ملكية أرض/منزل','فرز أرض','رهن عقار','إصدار كشف مساحة'
            ],
            'وزارة العدل والشؤون القانونية': [
                'تصديق عقود البيع','الوكالات العامة والخاصة','فسخ العقود','توثيق الرهون'
            ],
            'وزارة العمل': [
                'تصريح استقدام عامل','تجديد عقد عمل','إلغاء تصريح عمل','تغيير جهة العمل'
            ],
            'شرطة عمان السلطانية': [
                'تجديد مركبة','نقل ملكية مركبة','استخراج رخصة قيادة','إصدار بطاقة الأحوال المدنية','تجديد بطاقة الأحوال المدنية','إصدار شهادة ميلاد/وفاة','خدمات التأشيرات والإقامة'
            ],
            'وزارة التجارة والصناعة وترويج الاستثمار': [
                'إنشاء سجل تجاري جديد','تجديد السجل التجاري','تعديل بيانات السجل التجاري','شطب سجل تجاري'
            ],
            'البلديات': [
                'تصريح بناء','شهادة إتمام بناء','تصريح نشاط تجاري','تراخيص صحية'
            ],
            'وزارة الصحة': [
                'تصاريح مهن صحية','تراخيص منشآت طبية','شهادات صحية'
            ],
            'وزارة التربية والتعليم': [
                'معادلة شهادات','تصديق شهادات دراسية'
            ],
            'الهيئة العامة لسجل القوى العاملة': [
                'تسجيل باحث عن عمل','تحديث بيانات الباحث عن عمل'
            ],
            'هيئة الكهرباء والمياه والاتصالات': [
                'دفع فواتير الكهرباء والمياه','الاستفسار عن الاشتراكات','طلبات توصيل جديدة'
            ],
            'هيئة الاتصالات وتقنية المعلومات': [
                'دفع فواتير شركات الاتصالات','إعادة شحن الرصيد','الاشتراك في بعض الخدمات الإلكترونية'
            ],
        }

        for m_name, services in name_to_services.items():
            ministry = Ministry.query.filter_by(name=m_name).first()
            if not ministry:
                ministry = Ministry(name=m_name)
                db.session.add(ministry)
                db.session.flush()
            for s_name in services:
                if not Service.query.filter_by(ministry_id=ministry.id, name=s_name).first():
                    db.session.add(Service(ministry_id=ministry.id, name=s_name))

        db.session.commit()
        click.echo('Seeded ministries and services.')

        # Managed transactions catalog
        catalog = {
            'وزارة الإسكان والتخطيط العمراني': [
                ('استخراج سند ملكية',''),
                ('نقل ملكية أرض/منزل',''),
                ('فرز أرض',''),
                ('رهن عقار',''),
                ('إصدار كشف مساحة',''),
            ],
            'وزارة العدل والشؤون القانونية': [
                ('تصديق عقود البيع',''),
                ('الوكالات العامة والخاصة',''),
                ('فسخ العقود',''),
                ('توثيق الرهون',''),
            ],
            'وزارة العمل': [
                ('تصريح استقدام عامل',''),
                ('تجديد عقد عمل',''),
                ('إلغاء تصريح عمل',''),
                ('تغيير جهة العمل',''),
            ],
            'شرطة عمان السلطانية': [
                ('تجديد مركبة',''),
                ('نقل ملكية مركبة',''),
                ('استخراج رخصة قيادة',''),
                ('إصدار بطاقة الأحوال المدنية',''),
                ('تجديد بطاقة الأحوال المدنية',''),
                ('إصدار شهادة ميلاد/وفاة',''),
                ('خدمات التأشيرات والإقامة',''),
            ],
            'وزارة التجارة والصناعة وترويج الاستثمار': [
                ('إنشاء سجل تجاري جديد',''),
                ('تجديد السجل التجاري',''),
                ('تعديل بيانات السجل التجاري',''),
                ('شطب سجل تجاري',''),
            ],
            'البلديات': [
                ('تصريح بناء',''),
                ('شهادة إتمام بناء',''),
                ('تصريح نشاط تجاري',''),
                ('تراخيص صحية',''),
            ],
            'وزارة الصحة': [
                ('تصاريح مهن صحية',''),
                ('تراخيص منشآت طبية',''),
                ('شهادات صحية',''),
            ],
            'وزارة التربية والتعليم': [
                ('معادلة شهادات',''),
                ('تصديق شهادات دراسية',''),
            ],
            'الهيئة العامة لسجل القوى العاملة': [
                ('تسجيل باحث عن عمل',''),
                ('تحديث بيانات الباحث عن عمل',''),
            ],
            'هيئة الكهرباء والمياه والاتصالات': [
                ('دفع فواتير الكهرباء والمياه',''),
                ('الاستفسار عن الاشتراكات',''),
                ('طلبات توصيل جديدة',''),
            ],
            'هيئة الاتصالات وتقنية المعلومات': [
                ('دفع فواتير شركات الاتصالات',''),
                ('إعادة شحن الرصيد',''),
                ('الاشتراك في بعض الخدمات الإلكترونية',''),
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
