from app import create_app
from extensions import db
from models import User, Transaction, Expense

app = create_app()
with app.app_context():
    db.drop_all()
    db.create_all()

    # Users
    m = User(name="Manager", email="manager@sind.local", role="manager"); m.set_password("123456")
    f = User(name="Finance", email="finance@sind.local", role="finance"); f.set_password("123456")
    e = User(name="Employee", email="employee@sind.local", role="employee"); e.set_password("123456")
    db.session.add_all([m, f, e])
    db.session.commit()

    # Sample Transactions
    t1 = Transaction(title="معاملة تثمين عقاري", amount=150.0, owner_id=e.id, status="pending")
    t2 = Transaction(title="معاملة تقرير هندسي", amount=300.0, owner_id=e.id, status="completed")
    db.session.add_all([t1, t2])

    # Sample Expenses
    ex1 = Expense(description="إيجار مكتب", amount=500.0, created_by_id=f.id)
    ex2 = Expense(description="معدات مكتبية", amount=120.0, created_by_id=f.id)
    db.session.add_all([ex1, ex2])
    db.session.commit()
    print("Database seeded. Users: manager@sind.local, finance@sind.local, employee@sind.local (password 123456)")
