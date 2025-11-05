# سند — نظام مكتب خدمات (Python + HTML)

نظام مبدئي بلغة Flask لإدارة مكتب سند (العملاء، الخدمات، المعاملات، الفواتير) مع فصل رسوم الحكومة (Pass-Through) عن أتعاب المكتب واحتساب VAT 5% على الأتعاب فقط.

## تشغيل سريع (SQLite)
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac:
# source venv/bin/activate
pip install -r requirements.txt
flask db init
flask db migrate -m "init"
flask db upgrade
python -m app.seeds
flask run
```
ثم افتح: http://127.0.0.1:5000

## Docker + Postgres
```bash
cd infra
docker compose up --build
```
