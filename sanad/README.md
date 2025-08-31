# Sind ERP (Mini ERP in Flask)

نظام ERP مصغّر لإدارة مكتب سند: حسابات مستخدمين، معاملات، مصروفات. مبني على Flask + Bootstrap + SQLite.

## التشغيل محليًا
```bash
python -m venv .venv
source .venv/bin/activate  # على ويندوز: .venv\Scripts\activate
pip install -r requirements.txt

# إنشاء قاعدة البيانات + بيانات افتراضية
python seed.py

# تشغيل السيرفر
flask --app app run --debug
```

### حسابات افتراضية
- المدير: manager@sind.local / 123456
- المالية: finance@sind.local / 123456
- الموظف: employee@sind.local / 123456
