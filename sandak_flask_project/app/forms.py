from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Email, Optional

class LoginForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired(message='الرجاء إدخال اسم المستخدم')])
    password = PasswordField('كلمة المرور', validators=[DataRequired(message='الرجاء إدخال كلمة المرور')])
    remember = BooleanField('تذكرني')
    submit = SubmitField('تسجيل الدخول')


class ClientForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    phone = StringField('Phone', validators=[Optional()])
    email = StringField('Email', validators=[Optional(), Email()])
    national_id = StringField('National ID', validators=[Optional()])
    submit = SubmitField('Save')





class TransactionForm(FlaskForm):
    client_id = StringField('Client ID', validators=[DataRequired()])
    service_type = StringField('Service Type', validators=[DataRequired()])
    office = StringField('Office', validators=[Optional()])
    fee = DecimalField('Fee', places=2, validators=[Optional()])
    details = TextAreaField('Details', validators=[Optional()])
    submit = SubmitField('Create')
