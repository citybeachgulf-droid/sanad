# نظام إدارة مكاتب سند — مشروع بايثون + فلاسک (Starter)

محتويات:
- app/__init__.py   -> تهيئة التطبيق وملحقاته
- app/models.py     -> نماذج قاعدة البيانات (SQLAlchemy)
- app/forms.py      -> WTForms للنماذج الأساسية
- app/routes.py     -> مسارات Flask (Blueprints)
- app/auth.py       -> مصادقة المستخدمين (login/logout)
- app/templates/    -> قالب Jinja بسيط (index.html, login.html, dashboard.html)
- config.py         -> إعدادات التطبيق
- run.py            -> نقطة الدخول
- requirements.txt  -> الحزم المطلوبة

تشغيل محلي سريع:
1. python -m venv venv
2. source venv/bin/activate  # أو venv\Scripts\activate على ويندوز
3. pip install -r requirements.txt
4. export FLASK_APP=run.py  (او set FLASK_APP=run.py على ويندوز)
5. flask db init; flask db migrate -m "init"; flask db upgrade
6. flask run

قاعدة بيانات افتراضية: SQLite (config.py). لتغيير إلى PostgreSQL غيّر URI في config.py
