from pybo import db
from datetime import datetime
import pytz


def kst_now():
    return datetime.now(pytz.timezone('Asia/Seoul'))

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text(), nullable=False)
    name = db.Column(db.Text(), nullable=True)
    create_date = db.Column(db.DateTime(), nullable=False)
    users_id = db.Column(db.Integer, db.ForeignKey('users.users_id', ondelete='CASCADE'), nullable=False)
    users = db.relationship('Users', backref=db.backref('question_set'))
    makeorder_no = db.Column(db.String(200), nullable=True)
    barcode1 = db.Column(db.String(200), nullable=True)
    barcode2 = db.Column(db.String(200), nullable=True)
    barcode3 = db.Column(db.String(200), nullable=True)
    barcode4 = db.Column(db.String(200), nullable=True)
    barcode5 = db.Column(db.String(200), nullable=True)
    udi_one = db.Column(db.String(200), nullable=True)
    udi_box = db.Column(db.String(200), nullable=True)
    qr_code = db.Column(db.String(200), nullable=True)
    modify_date = db.Column(db.DateTime(), nullable=True)

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id', ondelete='CASCADE'))
    question = db.relationship('Question', backref=db.backref('answer_set'))
    content = db.Column(db.Text(), nullable=False)
    create_date = db.Column(db.DateTime(), nullable=False)
    users_id = db.Column(db.Integer, db.ForeignKey('users.users_id', ondelete='CASCADE'), nullable=False)
    users = db.relationship('Users', backref=db.backref('answer_set'))
    modify_date = db.Column(db.DateTime(), nullable=True)

class Users(db.Model):
    users_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    department = db.Column(db.String(120), nullable=False)
    jobtitle = db.Column(db.String(120), nullable=False)
    phonenumber = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), unique=True, nullable=False)
    createdate = db.Column(db.DateTime, default=kst_now)
    updatedate = db.Column(db.DateTime, default=kst_now, onupdate=kst_now)


class Users_Roles(db.Model):
    users_roles_id = db.Column(db.Integer, primary_key=True)
    users_id = db.Column(db.Integer, db.ForeignKey('users.users_id', ondelete='cascade', name='fk_users_roles_users_id'), nullable=False)
    roles_id = db.Column(db.Integer, db.ForeignKey('roles.roles_id', ondelete='cascade', name='fk_users_roles_roles_id'), nullable=False)

class Roles(db.Model):
    roles_id = db.Column(db.Integer, primary_key=True)
    rolename = db.Column(db.String(120), unique=True, nullable=False)
    createdate = db.Column(db.DateTime, default=kst_now)
    updatedate = db.Column(db.DateTime, default=kst_now, onupdate=kst_now)

class permissions(db.Model):
    permissions_id = db.Column(db.Integer, primary_key=True)
    permissions_name = db.Column(db.String(120), unique=True, nullable=False)
    createdate = db.Column(db.DateTime, default=kst_now)
    updatedate = db.Column(db.DateTime, default=kst_now, onupdate=kst_now)


class Roles_Permissions(db.Model):
    roles_permissions_id = db.Column(db.Integer, primary_key=True)
    roles_id = db.Column(db.Integer, db.ForeignKey('roles.roles_id', ondelete='cascade', name='fk_roles_permissions_roles_id'), nullable=False)
    permissions_id = db.Column(db.Integer, db.ForeignKey('permissions.permissions_id', ondelete='cascade', name='fk_roles_permissions_permissions_id'), nullable=False)

class ImportDataPO(db.Model):
    PRODT_ORDER_NO = db.Column(db.String, primary_key=True)
    PLANT_CD = db.Column(db.String)
    ITEM_CD = db.Column(db.String)
    PLAN_START_DT = db.Column(db.Date)
    PLAN_COMPT_DT = db.Column(db.Date)
    ORDER_QTY_IN_BASE_UNIT = db.Column(db.Integer)
    PROD_QTY_IN_ORDER_UNIT = db.Column(db.Integer)
    ORDER_STATUS = db.Column(db.String)
    RCPT_QTY_IN_ORDER_UNIT = db.Column(db.Integer)
    RCPT_QTY_IN_BASE_UNIT = db.Column(db.Integer)
    RCPT_FLG = db.Column(db.String)
























#  -- 하단은 ERP DB --

class ProductionOrderHeader(db.Model):
    __bind_key__ = 'mssql'
    __tablename__ = 'P_PRODUCTION_ORDER_HEADER'

    prodt_order_no = db.Column(db.String, primary_key=True)
    plant_cd = db.Column(db.String)
    item_cd = db.Column(db.String)
    plan_start_dt = db.Column(db.Date)
    plan_compt_dt = db.Column(db.Date)
    order_qty_in_base_unit = db.Column(db.Integer)
    prod_qty_in_order_unit = db.Column(db.Integer)
    order_status = db.Column(db.String)
    results = db.relationship('ProductionResults', back_populates='order', uselist=False)

class ProductionResults(db.Model):
    __bind_key__ = 'mssql'
    __tablename__ = 'P_PRODUCTION_RESULTS'

    prodt_order_no = db.Column(db.String, db.ForeignKey('P_PRODUCTION_ORDER_HEADER.prodt_order_no'), primary_key=True)
    rcpt_qty_in_order_unit = db.Column(db.Integer)
    rcpt_qty_in_base_unit = db.Column(db.Integer)
    rcpt_flg = db.Column(db.String)
    order = db.relationship('ProductionOrderHeader', back_populates='results')