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
                    conn.execute(text("ALTER TABLE transaction ADD COLUMN status VARCHAR(50) DEFAULT 'in_progress'"))

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
        """Seed ministries/services and the generic organizations catalog with services."""
        from app.models import Ministry, Service, User, ManagedTransaction, Organization, OrgService

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

        # ---------------- Seed Organizations Catalog ----------------
        org_defs = [
            {
                'name': 'وزارة التجارة',
                'kind': 'حكومي',
                'services': [
                    'إصدار وتجديد الرخص التجارية',
                    'تسجيل الشركات والمؤسسات الجديدة',
                    'تعديل بيانات الشركات القائمة',
                    'متابعة المخالفات التجارية',
                    'إصدار شهادات تسجيل الشركات أو تراخيصها',
                ],
            },
            {
                'name': 'الشرطة',
                'kind': 'حكومي',
                'services': [
                    'إصدار السجلات الجنائية (شهادات حسن السيرة والسلوك)',
                    'متابعة البلاغات والشكاوى',
                    'إصدار تصاريح المركبات والأوراق الرسمية',
                    'تحديث بيانات أفراد الشرطة',
                    'تقديم خدمات التحقق الأمني والتحريات',
                ],
            },
            {
                'name': 'وزارة الإسكان',
                'kind': 'حكومي',
                'services': [
                    'تسجيل طلبات السكن الحكومي',
                    'تقييم واستحقاق المشاريع العقارية',
                    'إصدار تصاريح البناء والتطوير',
                    'متابعة الشكاوى المتعلقة بالعقارات الحكومية',
                    'أرشفة مستندات الملكية العقارية',
                ],
            },
            {
                'name': 'البلدية',
                'kind': 'حكومي',
                'services': [
                    'إصدار تراخيص البناء والتجديد',
                    'متابعة تصاريح الأنشطة التجارية',
                    'إصدار تصاريح السلامة والصحة العامة',
                    'مراقبة المخالفات البيئية والصحية',
                    'تقديم تقارير تفتيش للمباني والمنشآت',
                ],
            },
            {
                'name': 'الجمارك',
                'kind': 'حكومي',
                'services': [
                    'إصدار تصاريح استيراد وتصدير البضائع',
                    'متابعة الرسوم الجمركية والضرائب',
                    'إصدار شهادات المنشأ والمستندات الجمركية',
                    'التفتيش والمطابقة على البضائع المستوردة',
                    'أرشفة السجلات الجمركية',
                ],
            },
            {
                'name': 'البنوك',
                'kind': 'خاص',
                'services': [
                    'طلبات التمويل العقاري والمركبات',
                    'التقييمات العقارية والمركبات المطلوبة من البنك',
                    'متابعة السداد والفواتير',
                    'إصدار شهادات الضمان أو القروض',
                ],
            },
            {
                'name': 'شركات التأمين',
                'kind': 'خاص',
                'services': [
                    'إصدار وثائق التأمين على العقارات والمركبات',
                    'تعديل وتجديد وثائق التأمين',
                    'تقديم تعويضات الحوادث والخسائر',
                    'متابعة السجلات والمطالبات التأمينية',
                ],
            },
            {
                'name': 'مزودي الخدمات العقارية',
                'kind': 'شريك',
                'services': [
                    'تقييم العقارات للبيع والإيجار',
                    'إدارة عقود البيع والإيجار',
                    'متابعة صيانة العقارات',
                    'أرشفة مستندات الملكية والعقود',
                ],
            },
            {
                'name': 'مزودي الخدمات للمركبات',
                'kind': 'شريك',
                'services': [
                    'تقييم المركبات (سيارات، شاحنات، معدات)',
                    'تحديث بيانات المركبات (لوحات، مالك، حالة)',
                    'متابعة الصيانة والفحص الدوري',
                    'أرشفة مستندات المركبات (الملكية، التأمين، الفحص الفني)',
                ],
            },
            {
                'name': 'العملاء والمستأجرين',
                'kind': 'خاص',
                'services': [
                    'تسجيل العملاء وفتح ملفات',
                    'تحديث بيانات العملاء',
                    'متابعة المدفوعات والفواتير',
                    'إشعارات بالمواعيد والفواتير',
                    'أرشفة العقود والفواتير الخاصة بكل عميل',
                ],
            },
        ]

        default_descriptions = {
            'إصدار وتجديد الرخص التجارية': 'خدمة إصدار أو تجديد الرخص التجارية بشكل نظامي.',
            'تسجيل الشركات والمؤسسات الجديدة': 'تسجيل كيانات جديدة مع البيانات الأساسية.',
            'تعديل بيانات الشركات القائمة': 'تحديث بيانات الشركات المسجلة.',
            'متابعة المخالفات التجارية': 'إدارة ومتابعة المخالفات.',
            'إصدار شهادات تسجيل الشركات أو تراخيصها': 'شهادات رسمية لتسجيل أو ترخيص الشركات.',
            'إصدار السجلات الجنائية (شهادات حسن السيرة والسلوك)': 'شهادة سجل جنائي للمواطنين والمقيمين.',
            'متابعة البلاغات والشكاوى': 'إدارة البلاغات والشكاوى الأمنية.',
            'إصدار تصاريح المركبات والأوراق الرسمية': 'تصاريح ولوحات ووثائق المركبات.',
            'تحديث بيانات أفراد الشرطة': 'تحديث ملفات موظفي الشرطة.',
            'تقديم خدمات التحقق الأمني والتحريات': 'التحقق الأمني وإجراءات التحري.',
            'تسجيل طلبات السكن الحكومي': 'استقبال طلبات السكن للمستحقين.',
            'تقييم واستحقاق المشاريع العقارية': 'دراسة وتقييم المشاريع العقارية الحكومية.',
            'إصدار تصاريح البناء والتطوير': 'تصاريح بناء وتطوير ضمن الاختصاص.',
            'متابعة الشكاوى المتعلقة بالعقارات الحكومية': 'إدارة شكاوى السكن والعقارات.',
            'أرشفة مستندات الملكية العقارية': 'حفظ وأرشفة الوثائق العقارية.',
            'إصدار تراخيص البناء والتجديد': 'تراخيص بناء أو ترميم من البلدية.',
            'متابعة تصاريح الأنشطة التجارية': 'تصاريح الأنشطة ضمن الاختصاص.',
            'إصدار تصاريح السلامة والصحة العامة': 'تصاريح الصحة والسلامة للمرافق.',
            'مراقبة المخالفات البيئية والصحية': 'رقابة وإنذارات للمخالفات.',
            'تقديم تقارير تفتيش للمباني والمنشآت': 'تقارير تفتيش دورية.',
            'إصدار تصاريح استيراد وتصدير البضائع': 'تصاريح عبور البضائع.',
            'متابعة الرسوم الجمركية والضرائب': 'تحصيل ومتابعة الرسوم.',
            'إصدار شهادات المنشأ والمستندات الجمركية': 'وثائق وشهادات منشأ.',
            'التفتيش والمطابقة على البضائع المستوردة': 'تفتيش ومطابقة المواصفات.',
            'أرشفة السجلات الجمركية': 'حفظ السجلات الجمركية.',
            'طلبات التمويل العقاري والمركبات': 'طلبات تمويل للعملاء.',
            'التقييمات العقارية والمركبات المطلوبة من البنك': 'تقييمات لأغراض التمويل.',
            'متابعة السداد والفواتير': 'إدارة السداد والفوترة.',
            'إصدار شهادات الضمان أو القروض': 'شهادات ضمان/قروض.',
            'إصدار وثائق التأمين على العقارات والمركبات': 'وثائق تأمين متنوعة.',
            'تعديل وتجديد وثائق التأمين': 'تعديل وتجديد الوثائق.',
            'تقديم تعويضات الحوادث والخسائر': 'مطالبات وتعويضات.',
            'متابعة السجلات والمطالبات التأمينية': 'متابعة ملفات المطالبات.',
            'تقييم العقارات للبيع والإيجار': 'خدمات تقييم للعقارات.',
            'إدارة عقود البيع والإيجار': 'إدارة العقود.',
            'متابعة صيانة العقارات': 'خطط وصيانة دورية.',
            'أرشفة مستندات الملكية والعقود': 'حفظ الوثائق.',
            'تقييم المركبات (سيارات، شاحنات، معدات)': 'فحص وتقييم المركبات.',
            'تحديث بيانات المركبات (لوحات، مالك، حالة)': 'تحديث سجلات المركبات.',
            'متابعة الصيانة والفحص الدوري': 'الصيانة والفحص الدوري.',
            'أرشفة مستندات المركبات (الملكية، التأمين، الفحص الفني)': 'حفظ وثائق المركبات.',
            'تسجيل العملاء وفتح ملفات': 'إنشاء ملفات العملاء.',
            'تحديث بيانات العملاء': 'تعديل بيانات العملاء.',
            'متابعة المدفوعات والفواتير': 'تتبع المدفوعات.',
            'إشعارات بالمواعيد والفواتير': 'تنبيهات ومراسلات.',
            'أرشفة العقود والفواتير الخاصة بكل عميل': 'حفظ عقود وفواتير.',
        }

        created_orgs = 0
        created_svcs = 0
        for org_def in org_defs:
            org = Organization.query.filter_by(name=org_def['name']).first()
            if not org:
                org = Organization(name=org_def['name'], kind=org_def['kind'])
                db.session.add(org)
                db.session.flush()
                created_orgs += 1
            for s_name in org_def['services']:
                exists = OrgService.query.filter_by(organization_id=org.id, name=s_name).first()
                if not exists:
                    db.session.add(OrgService(
                        organization_id=org.id,
                        name=s_name,
                        description=default_descriptions.get(s_name, ''),
                        is_active=True,
                    ))
                    created_svcs += 1

        if created_orgs or created_svcs:
            db.session.commit()
        click.echo(f'Seeded organizations: {created_orgs} orgs, {created_svcs} services.')

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
