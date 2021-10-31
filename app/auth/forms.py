from app import email
from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,BooleanField, SubmitField,ValidationError
from wtforms.validators import DataRequired, Length ,Email,Regexp,EqualTo
from ..models import User

class LoginForm(FlaskForm):
    email = StringField('Email',validators=[DataRequired(), Length(1,64),Email()])
    password = PasswordField('Password', validators = [DataRequired()])
    remember_me = BooleanField('Keep me logged in')
    sumbmit = SubmitField('Log In')
class RegistrationForm(FlaskForm):
    email = StringField('Email',validators=[DataRequired(),Length(1,64),Email()])
    username = StringField('Username', validators=[
        DataRequired(),Length(1,64),Regexp(
            '^[A-Za-z][A-Za-z0-9_.]*$',0,
            '用户名只能用英文字母，数字，或者下划线'
        )])
    password = PasswordField('Password',validators=[DataRequired(), EqualTo('password2',message ='两次密码必须相同')])
    password2 = PasswordField('Confirm Password',validators = [DataRequired()])
    submit = SubmitField('Register')
    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email has already used')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username has already used')
class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old password', validators=[DataRequired()])
    password = PasswordField('New password', validators=[DataRequired(),EqualTo('password2',message='两次新密码必须相同')])
    password2 = PasswordField('confirm new password', validators=[DataRequired()])
    submit = SubmitField('Update password')