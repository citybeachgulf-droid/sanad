import sqlite3
from pathlib import Path
from datetime import datetime


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS managed_transactions (
            id INTEGER PRIMARY KEY,
            authority VARCHAR(200) NOT NULL,
            service VARCHAR(200) NOT NULL,
            description TEXT,
            fee NUMERIC NOT NULL DEFAULT 0,
            status VARCHAR(50) NOT NULL DEFAULT 'نشطة',
            is_paid BOOLEAN DEFAULT 0,
            paid_amount NUMERIC DEFAULT 0,
            paid_at DATETIME,
            created_at DATETIME,
            updated_at DATETIME
        )
        """
    )
    # Unique pair for idempotency
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mt_auth_service
        ON managed_transactions(authority, service)
        """
    )


def seed(conn: sqlite3.Connection) -> int:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    catalog = {
        'وزارة الإسكان والتخطيط العمراني': [
            'استخراج سند ملكية',
            'نقل ملكية أرض/منزل',
            'فرز أرض',
            'رهن عقار',
            'إصدار كشف مساحة',
        ],
        'وزارة العدل والشؤون القانونية': [
            'تصديق عقود البيع',
            'الوكالات العامة والخاصة',
            'فسخ العقود',
            'توثيق الرهون',
        ],
        'وزارة العمل': [
            'تصريح استقدام عامل',
            'تجديد عقد عمل',
            'إلغاء تصريح عمل',
            'تغيير جهة العمل',
        ],
        'شرطة عمان السلطانية': [
            'تجديد مركبة',
            'نقل ملكية مركبة',
            'استخراج رخصة قيادة',
            'إصدار بطاقة الأحوال المدنية',
            'تجديد بطاقة الأحوال المدنية',
            'إصدار شهادة ميلاد/وفاة',
            'خدمات التأشيرات والإقامة',
        ],
        'وزارة التجارة والصناعة وترويج الاستثمار': [
            'إنشاء سجل تجاري جديد',
            'تجديد السجل التجاري',
            'تعديل بيانات السجل التجاري',
            'شطب سجل تجاري',
        ],
        'البلديات': [
            'تصريح بناء',
            'شهادة إتمام بناء',
            'تصريح نشاط تجاري',
            'تراخيص صحية',
        ],
        'وزارة الصحة': [
            'تصاريح مهن صحية',
            'تراخيص منشآت طبية',
            'شهادات صحية',
        ],
        'وزارة التربية والتعليم': [
            'معادلة شهادات',
            'تصديق شهادات دراسية',
        ],
        'الهيئة العامة لسجل القوى العاملة': [
            'تسجيل باحث عن عمل',
            'تحديث بيانات الباحث عن عمل',
        ],
        'هيئة الكهرباء والمياه والاتصالات': [
            'دفع فواتير الكهرباء والمياه',
            'الاستفسار عن الاشتراكات',
            'طلبات توصيل جديدة',
        ],
        'هيئة الاتصالات وتقنية المعلومات': [
            'دفع فواتير شركات الاتصالات',
            'إعادة شحن الرصيد',
            'الاشتراك في بعض الخدمات الإلكترونية',
        ],
    }

    # Detect columns for compatibility
    cols = {row[1] for row in conn.execute("PRAGMA table_info(managed_transactions)")}
    fields = ['authority', 'service']
    if 'description' in cols:
        fields.append('description')
    if 'fee' in cols:
        fields.append('fee')
    if 'status' in cols:
        fields.append('status')
    if 'created_at' in cols:
        fields.append('created_at')
    if 'updated_at' in cols:
        fields.append('updated_at')

    placeholders = ','.join(['?'] * len(fields))
    sql = f"INSERT OR IGNORE INTO managed_transactions ({','.join(fields)}) VALUES ({placeholders})"

    inserted = 0
    for authority, services in catalog.items():
        for service in services:
            values = [authority, service]
            if 'description' in fields:
                values.append('')
            if 'fee' in fields:
                values.append(0)
            if 'status' in fields:
                values.append('نشطة')
            if 'created_at' in fields:
                values.append(now)
            if 'updated_at' in fields:
                values.append(now)
            conn.execute(sql, values)
            inserted += 1
    conn.commit()
    return inserted


def main():
    db_path = Path(__file__).parent / 'sandak.db'
    conn = sqlite3.connect(str(db_path))
    try:
        ensure_table(conn)
        count = seed(conn)
        print(f"Seeded managed_transactions: {count} entries processed (idempotent).")
    finally:
        conn.close()


if __name__ == '__main__':
    main()

