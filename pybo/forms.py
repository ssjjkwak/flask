from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, PasswordField, EmailField
from wtforms.fields.choices import SelectField
from wtforms.fields.simple import SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, Email

class QuestionForm(FlaskForm):
    code = StringField('코드', validators=[DataRequired('코드는 필수입력 항목입니다.')])
    name = StringField('품목명', validators=[DataRequired('품목명은 필수입력 항목입니다.')])
    content = StringField('비고', validators=[DataRequired('비고는 필수입력 항목입니다.')])
    makeorder_no = StringField('제조오더번호', validators=[DataRequired('제조오더번호는 필수입력 항목입니다.')])
    barcode1 = StringField('바코드#1', validators=[DataRequired('바코드는 필수입력 항목입니다.')])
    barcode2 = StringField('바코드#2', validators=[DataRequired('바코드는 필수입력 항목입니다.')])
    barcode3 = StringField('바코드#3', validators=[DataRequired('바코드는 필수입력 항목입니다.')])
    barcode4 = StringField('바코드#4', validators=[DataRequired('바코드는 필수입력 항목입니다.')])
    barcode5 = StringField('바코드#5', validators=[DataRequired('바코드는 필수입력 항목입니다.')])
    udi_one = StringField('UDI(Unit)', validators=[DataRequired('UDI코드는 필수입력 항목입니다.')])
    udi_box = StringField('UDI(Box)', validators=[DataRequired('UDI코드는 필수입력 항목입니다.')])
    qr_code = StringField('QR코드', validators=[DataRequired('QR코드는 필수입력 항목입니다.')])


class AnswerForm(FlaskForm):
    content = TextAreaField('내용', validators=[DataRequired('내용은 필수입력 항목입니다.')])

class UserCreateForm(FlaskForm):
    USR_ID = StringField('사용자이름', validators=[DataRequired('아이디는 필수입력 항목입니다.'), Length(min=3, max=25)])
    USR_PW1 = PasswordField('비밀번호', validators=[
        DataRequired('비밀번호는 필수입력 항목입니다.'), EqualTo('USR_PW2', '비밀번호가 일치하지 않습니다')])
    USR_PW2 = PasswordField('비밀번호확인', validators=[DataRequired('비밀번호 확인은 필수입력 항목입니다.')])
    USR_EMAIL = EmailField('이메일', validators=[DataRequired('이메일은 필수입력 항목입니다.'), Email()])
    USR_NM = StringField('이름', validators=[DataRequired()])
    USR_JOB = StringField('직책/직위', validators=[DataRequired()])
    USR_DEPT = StringField('부서', validators=[DataRequired()])
    USR_PHONE = StringField('전화번호', validators=[DataRequired()])


class UserLoginForm(FlaskForm):
    USR_ID = StringField('사용자이름', validators=[DataRequired(), Length(min=3, max=25)])
    USR_PW = PasswordField('비밀번호', validators=[DataRequired()])

class UserModifyForm(FlaskForm):

    old_USR_PW = PasswordField('기존비밀번호', validators=[
        DataRequired('기존 비밀번호는 필수입력 항목입니다.')])
    new_USR_PW1 = PasswordField('새 비밀번호', validators=[
        DataRequired('비밀번호는 필수입력 항목입니다.'), EqualTo('new_password2', '비밀번호가 일치하지 않습니다')])
    new_USR_PW2 = PasswordField('새 비밀번호확인', validators=[
        DataRequired('비밀번호 확인은 필수입력 항목입니다.')])

class UserUpdateForm(FlaskForm):
    USR_ID = StringField('사용자ID', validators=[DataRequired(), Length(min=2, max=20)])
    USR_NM = StringField('성명', validators=[DataRequired(), Length(min=2, max=50)])
    USR_EMAIL = StringField('이메일', validators=[DataRequired(), Email()])
    USR_PW1 = PasswordField('비밀번호', validators=[DataRequired('비밀번호를 입력하세요'), EqualTo('USR_PW2', '비밀번호가 일치하지 않습니다')])
    USR_PW2 = PasswordField('비밀번호확인', validators=[DataRequired('비밀번호 확인을 입력하세요')])
    USR_DEPT = StringField('부서', validators=[DataRequired()])
    USR_JOB = StringField('직위/직책', validators=[DataRequired()])
    USR_PHONE = StringField('전화번호', validators=[DataRequired()])



