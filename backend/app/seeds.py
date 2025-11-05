from .extensions import db
from .models import Service, Customer
from . import create_app

def run():
    app = create_app()
    with app.app_context():
        if not Service.query.first():
            db.session.add(Service(name='تجديد إقامة عامل', gov_entity='وزارة العمل', office_fee=3, gov_fee_type='fixed', gov_fee_value=10, vat_applicable=True))
            db.session.add(Service(name='تجديد سجل تجاري', gov_entity='وزارة التجارة', office_fee=5, gov_fee_type='variable', gov_fee_value=0, vat_applicable=True))
        if not Customer.query.first():
            db.session.add(Customer(full_name='أحمد بن سالم', phone='9xxxxxxx'))
        db.session.commit()

if __name__ == '__main__':
    run()
