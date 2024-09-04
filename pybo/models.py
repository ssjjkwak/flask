from sqlalchemy.orm import relationship, backref, foreign

from pybo import db
from datetime import datetime
from sqlalchemy import Column, Integer, Numeric, Index
from sqlalchemy.dialects.mssql import NVARCHAR
from flask_sqlalchemy import SQLAlchemy
import pytz


def kst_now():
    return datetime.now(pytz.timezone('Asia/Seoul'))

# 사용자
class User(db.Model):
    __tablename__ = 'Z_USER'
    __table_args__ = {'schema': 'dbo'}

    USR_ID = db.Column(db.VARCHAR(20), primary_key=True)
    USR_PW = db.Column(db.VARCHAR(255), nullable=True)
    USR_NM = db.Column(db.VARCHAR(255), nullable=True)
    USR_EMAIL = db.Column(db.VARCHAR(40), nullable=True)
    USR_DEPT = db.Column(db.VARCHAR(20), nullable=True)
    USR_JOB = db.Column(db.VARCHAR(10), nullable=True)
    USR_PHONE = db.Column(db.VARCHAR(15), nullable=False)
    ROLE_ID = db.Column(db.VARCHAR(10), nullable=False)
    INSRT_DT = db.Column(db.DateTime, default=kst_now)
    UPDT_DT = db.Column(db.DateTime, default=kst_now, onupdate=kst_now)

class Role(db.Model):
    __tablename__ = 'Z_ROLE'
    __table_args__ = {'schema': 'dbo'}

    ROLE_ID = db.Column(db.VARCHAR(10), primary_key=True)
    ROLE_NM = db.Column(db.VARCHAR(20), nullable=True)
    REMARK = db.Column(db.VARCHAR(50), nullable=True)
    INSRT_DT = db.Column(db.DateTime, default=kst_now)
    UPDT_DT = db.Column(db.DateTime, default=kst_now, onupdate=kst_now)


class UserRole(db.Model):
    __tablename__ = 'Z_USER_ROLE'
    __table_args__ = {'schema': 'dbo'}

    USR_ID = db.Column(db.VARCHAR(20), db.ForeignKey('dbo.Z_USER.USR_ID'), primary_key=True)
    ROLE_ID = db.Column(db.VARCHAR(10), db.ForeignKey('dbo.Z_ROLE.ROLE_ID'), primary_key=True)
    INSRT_DT = db.Column(db.DateTime, default=kst_now)
    UPDT_DT = db.Column(db.DateTime, default=kst_now, onupdate=kst_now)

    user = db.relationship('User', backref=db.backref('user_roles', cascade='all, delete-orphan'))
    role = db.relationship('Role', backref=db.backref('user_roles', cascade='all, delete-orphan'))



# 기준정보
class Item(db.Model):
    __tablename__ = 'B_ITEM'
    __table_args__ = {'schema': 'dbo'}

    PLANT_CD = db.Column(db.NVARCHAR(4), nullable=True)
    ITEM_CD = db.Column(db.NVARCHAR(50), primary_key=True)
    ITEM_NM = db.Column(db.NVARCHAR(100), nullable=True)
    SPEC = db.Column(db.NVARCHAR(20), nullable=True)
    ITEM_ACCT = db.Column(db.NCHAR(2), nullable=True)
    BASIC_UNIT = db.Column(db.NVARCHAR(3), nullable=True)
    ITEM_GROUP_CD = db.Column(db.NVARCHAR(50), nullable=True)
    ALPHA_CODE = db.Column(db.NVARCHAR(50), nullable=True)
    UDI_CODE = db.Column(db.NVARCHAR(50), nullable=True)
    PRODUCT_NM = db.Column(db.NVARCHAR(100), nullable=True)
    MODEL_NM = db.Column(db.NVARCHAR(100), nullable=True)
    GTIN_CODE1 = db.Column(db.NVARCHAR(50), nullable=True)
    PAC_QTY1 = db.Column(db.NUMERIC(18,0), nullable=True)
    GTIN_CODE2 = db.Column(db.NVARCHAR(50), nullable=True)
    PAC_QTY2 = db.Column(db.NUMERIC(18,0), nullable=True)
    BARCODE_TYPE = db.Column(db.NVARCHAR(20), nullable=True)
    IF_INSRT_DT = db.Column(db.DateTime, default=kst_now)
    UPDT_DT = db.Column(db.DateTime, default=kst_now, onupdate=kst_now)
    UPDT_USR = db.Column(db.NVARCHAR(13), nullable=True)

class Item_Master(db.Model):
    __tablename__ = 'B_ITEM_MASTER'
    __table_args__ = {'schema': 'dbo'}

    ALPHA_CODE = db.Column(db.NVARCHAR(50), primary_key=True)
    DESCRIPTION = db.Column(db.NVARCHAR(50), nullable=True)

class Item_Group(db.Model):
    __tablename__ = 'B_ITEM_GROUP'
    __table_args__ = {'schema': 'dbo'}

    ITEM_GROUP_CD = db.Column(db.NVARCHAR(8), primary_key=True)
    ITEM_GROUP_NM = db.Column(db.NVARCHAR(100), nullable=True)
    UPPER_ITEM_GROUP_CD = db.Column(db.NVARCHAR(8), nullable=True)
    ITEM_GROUP_LEVEL = db.Column(db.NUMERIC(18,0), nullable=True)

class Plant(db.Model):
    __tablename__ = 'B_PLANT'
    __table_args__ = {'schema': 'dbo'}

    PLANT_CD = db.Column(db.NVARCHAR(4), primary_key=True)
    PLANT_NM = db.Column(db.NVARCHAR(14), nullable=True)
    CUR_CD = db.Column(db.NVARCHAR(4), nullable=True)

class Storage_Location(db.Model):
    __tablename__ = 'B_STORAGE_LOCATION'
    __table_args__ = {'schema': 'dbo'}

    SL_CD = db.Column(db.NVARCHAR(4), primary_key=True)
    SL_NM = db.Column(db.NVARCHAR(12), nullable=True)
    PLANT_CD = db.Column(db.NVARCHAR(4), nullable=True)

# 수불유형
class Movetype_Configuration(db.Model):
    __tablename__ = 'I_MOVETYPE_CONFIGURATION'
    __table_args__ = {'schema': 'dbo'}

    MOV_TYPE = db.Column(db.NVARCHAR(3), primary_key=True)
    MOV_TYPE_NM = db.Column(db.NVARCHAR(30), nullable=True)

# 발주정보
class Purchase_Order(db.Model):
    __tablename__ = 'M_PUR_ORD'
    __table_args__ = {'schema': 'dbo'}

    PO_NO = db.Column(db.NVARCHAR(18), primary_key=True)
    PO_SEQ_NO = db.Column(db.SMALLINT, primary_key=True)
    BP_CD = db.Column(db.NVARCHAR(10), nullable=True)
    PLANT_CD = db.Column(db.NVARCHAR(4), nullable=True)
    SL_CD = db.Column(db.NVARCHAR(4), nullable=True)
    ITEM_CD = db.Column(db.NVARCHAR(50), nullable=True)
    PO_QTY = db.Column(db.NUMERIC(18,6), nullable=True)
    OUT_QTY = db.Column(db.NUMERIC(18,6), nullable=True)
    IN_QTY = db.Column(db.NUMERIC(18,6), nullable=True)
    PO_UNIT = db.Column(db.NCHAR(3), nullable=True)
    PO_PRC = db.Column(db.NUMERIC(18,6), nullable=True)
    PO_DOC_AMT = db.Column(db.NUMERIC(18,2), nullable=True)
    PO_CUR = db.Column(db.NCHAR(3), nullable=True)
    DLVY_DT = db.Column(db.DATETIME, nullable=True)
    PO_TYPE_CD = db.Column(db.NVARCHAR(5), nullable=True)
    PUR_ORG = db.Column(db.NVARCHAR(4), nullable=True)
    PUR_GRP = db.Column(db.NVARCHAR(4), nullable=True)
    PUR_BIZ_AREA = db.Column(db.NVARCHAR(10), nullable=True)
    RCPT_TYPE = db.Column(db.NVARCHAR(5), nullable=True)
    IF_INSRT_DT = db.Column(db.DateTime, default=kst_now)
    IF_UPDT_DT = db.Column(db.DateTime, default=kst_now, onupdate=kst_now)
    STATUS = db.Column(db.NVARCHAR(4), nullable=True)

# 수주정보
class Sales_Order(db.Model):
    __tablename__ = 'S_SO'
    __table_args__ = {'schema': 'dbo'}

    SO_NO = db.Column(db.NVARCHAR(18), primary_key=True)
    SO_SEQ = db.Column(db.SMALLINT, primary_key=True)
    BP_CD = db.Column(db.NVARCHAR(10), nullable=True)
    PLANT_CD = db.Column(db.NVARCHAR(4), nullable=True)
    SL_CD = db.Column(db.NVARCHAR(4), nullable=True)
    ITEM_CD = db.Column(db.NVARCHAR(50), nullable=True)
    SO_PRICE = db.Column(db.NUMERIC(18,6), nullable=True)
    NET_AMT = db.Column(db.NUMERIC(18,2), nullable=True)
    ITEM_ACCT = db.Column(db.NCHAR(2), nullable=True)
    SO_QTY = db.Column(db.NUMERIC(18,6), nullable=True)
    BASE_UNIT = db.Column(db.NCHAR(3), nullable=True)
    IF_INSRT_DT = db.Column(db.DateTime, default=kst_now)
    IF_UPDT_DT = db.Column(db.DateTime, default=kst_now, onupdate=kst_now)

# 제조오더정보
class Production_Order(db.Model):
    __tablename__ = 'P_PRODUCTION_ORDER'
    __table_args__ = {'schema': 'dbo'}

    PRODT_ORDER_NO = db.Column(db.NVARCHAR(18), primary_key=True)
    PLANT_CD = db.Column(db.NVARCHAR(4), nullable=True)
    ITEM_CD = db.Column(db.NVARCHAR(50), nullable=True)
    OPR_NO = db.Column(db.NVARCHAR(3), nullable=True)
    WC_CD = db.Column(db.NVARCHAR(7), nullable=True)
    SL_CD = db.Column(db.NVARCHAR(10), nullable=True)
    PLANT_START_DT = db.Column(db.DATETIME, nullable=True)
    PRODT_ORDER_QTY = db.Column(db.NUMERIC(18,6), nullable=True)
    PRODT_ORDER_UNIT = db.Column(db.NVARCHAR(3), nullable=True)
    IF_INSRT_DT = db.Column(db.DateTime, default=kst_now)
    IF_UPDT_DT = db.Column(db.DateTime, default=kst_now, onupdate=kst_now)
    PLANT_COMPT_DT = db.Column(db.DATETIME, nullable=True)
    RELEASE_DT = db.Column(db.DATETIME, nullable=True)
    PROD_QTY_IN_ORDER_UNIT = db.Column(db.NUMERIC(18,6), nullable=True)
    BAD_QTY_IN_ORDER_UNIT = db.Column(db.NUMERIC(18,6), nullable=True)
    ORDER_STATUS = db.Column(db.NVARCHAR(4), nullable=True)

# 알파플랜 엑셀 파일
class Production_Alpha(db.Model):
    __tablename__ = 'P_PRODUCTION_ALPHA'
    __table_args__ = (
        {'schema': 'dbo'}
    )

    LOT = db.Column(db.NVARCHAR(8), nullable=True)
    product = db.Column(db.NVARCHAR(8), nullable=True)
    barcode = db.Column(db.NVARCHAR(20), primary_key=True)
    modified = db.Column(db.DateTime, primary_key=True)
    err_code = db.Column(db.NUMERIC(18,0), nullable=True)
    err_info = db.Column(db.NVARCHAR(50), nullable=True)
    print_time = db.Column(db.DateTime, nullable=True)
    inweight_time = db.Column(db.DateTime, nullable=True)
    inweight_cycles = db.Column(db.NUMERIC(18,0), nullable=True)
    inweight_station = db.Column(db.NUMERIC(18,0), nullable=True)
    inweight_result = db.Column(db.NUMERIC(18,0), nullable=True)
    inweight_value = db.Column(db.NUMERIC(18,0), nullable=True)
    leaktest_cycles = db.Column(db.NUMERIC(18,0), nullable=True)
    leaktest_entry = db.Column(db.DateTime, nullable=True)
    leaktest_exit = db.Column(db.DateTime, nullable=True)
    leaktest_station = db.Column(db.NUMERIC(18,0), nullable=True)
    leaktest_value = db.Column(db.NUMERIC(18,0), nullable=True)
    leaktest_ptest = db.Column(db.NUMERIC(18,0), nullable=True)
    leaktest_duration = db.Column(db.NUMERIC(18,0), nullable=True)
    leaktest_result = db.Column(db.NUMERIC(18,0), nullable=True)
    outweight_time = db.Column(db.DateTime, nullable=True)
    outweight_station = db.Column(db.NUMERIC(18,0), nullable=True)
    outweight_cycles = db.Column(db.NUMERIC(18,0), nullable=True)
    outweight_result = db.Column(db.NUMERIC(18,0), nullable=True)
    outweight_value = db.Column(db.NUMERIC(18,0), nullable=True)
    itest2_time = db.Column(db.DateTime, nullable=True)
    itest2_station = db.Column(db.NUMERIC(18,0), nullable=True)
    itest2_cycles = db.Column(db.NUMERIC(18,0), nullable=True)
    itest2_result = db.Column(db.NUMERIC(18,0), nullable=True)
    itest2_value = db.Column(db.NUMERIC(18,0), nullable=True)
    itest2_ptest = db.Column(db.NUMERIC(18,0), nullable=True)
    prodlabel_time = db.Column(db.DateTime, nullable=True)
    prodlabel_cycles = db.Column(db.NUMERIC(18,0), nullable=True)
    INSRT_DT = db.Column(db.DateTime, default=kst_now)
    INSRT_USR = db.Column(db.NVARCHAR(13), nullable=True)
    UPDT_DT = db.Column(db.DateTime, default=kst_now, onupdate=kst_now)
    UPDT_USR = db.Column(db.NVARCHAR(13), nullable=True)
    REPORT_FLAG = db.Column(db.NVARCHAR(2), nullable=True, default='N')


# 알파플랜 엑셀 파일에서 MODIFED만 제거
class Production_Barcode(db.Model):
    __tablename__ = 'P_PRODUCTION_BARCODE'
    __table_args__ = {'schema': 'dbo'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    LOT = db.Column(db.NVARCHAR(8), nullable=True)
    product = db.Column(db.NVARCHAR(8), nullable=True)
    barcode = db.Column(db.NVARCHAR(20), nullable=True)
    err_code = db.Column(db.NUMERIC(18, 0), nullable=True)
    err_info = db.Column(db.NVARCHAR(50), nullable=True)
    print_time = db.Column(db.DateTime, nullable=True)
    inweight_time = db.Column(db.DateTime, nullable=True)
    inweight_cycles = db.Column(db.NUMERIC(18, 0), nullable=True)
    inweight_station = db.Column(db.NUMERIC(18, 0), nullable=True)
    inweight_result = db.Column(db.NUMERIC(18, 0), nullable=True)
    inweight_value = db.Column(db.NUMERIC(18, 0), nullable=True)
    leaktest_cycles = db.Column(db.NUMERIC(18, 0), nullable=True)
    leaktest_entry = db.Column(db.DateTime, nullable=True)
    leaktest_exit = db.Column(db.DateTime, nullable=True)
    leaktest_station = db.Column(db.NUMERIC(18, 0), nullable=True)
    leaktest_value = db.Column(db.NUMERIC(18, 0), nullable=True)
    leaktest_ptest = db.Column(db.NUMERIC(18, 0), nullable=True)
    leaktest_duration = db.Column(db.NUMERIC(18, 0), nullable=True)
    leaktest_result = db.Column(db.NUMERIC(18, 0), nullable=True)
    outweight_time = db.Column(db.DateTime, nullable=True)
    outweight_station = db.Column(db.NUMERIC(18, 0), nullable=True)
    outweight_cycles = db.Column(db.NUMERIC(18, 0), nullable=True)
    outweight_result = db.Column(db.NUMERIC(18, 0), nullable=True)
    outweight_value = db.Column(db.NUMERIC(18, 0), nullable=True)
    itest2_time = db.Column(db.DateTime, nullable=True)
    itest2_station = db.Column(db.NUMERIC(18, 0), nullable=True)
    itest2_cycles = db.Column(db.NUMERIC(18, 0), nullable=True)
    itest2_result = db.Column(db.NUMERIC(18, 0), nullable=True)
    itest2_value = db.Column(db.NUMERIC(18, 0), nullable=True)
    itest2_ptest = db.Column(db.NUMERIC(18, 0), nullable=True)
    prodlabel_time = db.Column(db.DateTime, nullable=True)
    prodlabel_cycles = db.Column(db.NUMERIC(18, 0), nullable=True)
    INSRT_DT = db.Column(db.DateTime, default=kst_now)
    INSRT_USR = db.Column(db.NVARCHAR(13), nullable=True)
    UPDT_DT = db.Column(db.DateTime, default=kst_now, onupdate=kst_now)
    UPDT_USR = db.Column(db.NVARCHAR(13), nullable=True)
    REPORT_FLAG = db.Column(db.NVARCHAR(1), nullable=False, default='N')

class Production_Barcode_Assign(db.Model):
    __tablename__ = 'P_PRODUCTION_BARCODE_ASSN'
    __table_args__ = {'schema': 'dbo'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    barcode = db.Column(db.NVARCHAR(20), nullable=True)
    PRODT_ORDER_NO = db.Column(db.NVARCHAR(18), nullable=True)
    OPR_NO = db.Column(db.NVARCHAR(10), nullable=False, default='10')
    REPORT_TYPE = db.Column(db.NVARCHAR(5), nullable=True)
    BOX_NUM = db.Column(db.NVARCHAR(20), nullable=True)
    INSRT_DT = db.Column(db.DateTime, default=kst_now)
    INSRT_USR = db.Column(db.NVARCHAR(13), nullable=True)
    UPDT_DT = db.Column(db.DateTime, default=kst_now, onupdate=kst_now)
    UPDT_USR = db.Column(db.NVARCHAR(13), nullable=True)
    MOV_TYPE = db.Column(db.NVARCHAR(4), nullable=True)
    PO_NO = db.Column(db.NVARCHAR(18), nullable=True)
    PO_SEQ_NO = db.Column(db.SMALLINT, nullable=True)
    SO_NO = db.Column(db.NVARCHAR(18), nullable=True)
    SO_SEQ = db.Column(db.SMALLINT, nullable=True)
    WC_CD = db.Column(db.NVARCHAR(7), nullable=True)


class Production_Results(db.Model):
    __tablename__ = 'P_PRODUCTION_RESULTS'
    __table_args__ = {'schema': 'dbo'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    PRODT_ORDER_NO = db.Column(db.NVARCHAR(18), nullable=True)
    OPR_NO = db.Column(db.NVARCHAR(3), nullable=True)
    WC_CD = db.Column(db.NVARCHAR(7), nullable=True)
    SEQ = db.Column(db.SMALLINT, nullable=True)
    REPORT_TYPE = db.Column(db.NVARCHAR(5), nullable=True)
    TOTAL_QTY = db.Column(db.NUMERIC(18, 6), nullable=True)
    PLANT_CD = db.Column(db.NVARCHAR(4), nullable=True, default='p710')
    REPORT_DT = db.Column(db.DateTime, default=kst_now)
    INSRT_USR = db.Column(db.NVARCHAR(13), nullable=True)

# BOM
class Bom(db.Model):
    __tablename__ = 'P_BOM'
    __table_args__ = {'schema': 'dbo'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    PRNT_ITEM_CD = db.Column(db.NVARCHAR(50), nullable=True)
    PLANT_CD = db.Column(db.NVARCHAR(4), nullable=True)
    CHILD_ITEM_CD = db.Column(db.NVARCHAR(50), nullable=True)
    CHILD_ITEM_UNIT = db.Column(db.NVARCHAR(3), nullable=True)
    PRNT_ITEM_QTY = db.Column(db.NUMERIC(18,6),nullable=True)
    CHILD_ITEM_QTY = db.Column(db.NUMERIC(18,6),nullable=True)
    VALID_DT_FR = db.Column(db.DateTime, nullable=True)
    VALID_DT_TO = db.Column(db.DateTime, nullable=True)
    IF_INSRT_DT = db.Column(db.DateTime, default=kst_now)
    IF_UPDT_DT = db.Column(db.DateTime, default=kst_now)

    # Relationship to Item
    child_item = relationship('Item', primaryjoin=foreign(CHILD_ITEM_CD) == Item.ITEM_CD, backref=backref('boms', lazy=True))

# 작업장
class Work_Center(db.Model):
    __tablename__ = 'P_WORK_CENTER'
    __table_args__ = {'schema': 'dbo'}

    PLANT_CD = db.Column(db.NVARCHAR(4), nullable=True)
    WC_CD = db.Column(db.NVARCHAR(7), primary_key=True)
    WC_NM = db.Column(db.NVARCHAR(50), nullable=True)

class Packing_Hdr(db.Model):
    __tablename__ = 'P_PACKING_HDR'
    __table_args__ = {'schema': 'dbo'}

    prodt_order_no = db.Column(db.String(18), primary_key=True, nullable=False)
    m_box_no = db.Column(db.String(18), nullable=True)
    plant_start_dt = db.Column(db.DateTime, nullable=True)
    prodt_order_qty = db.Column(db.Numeric(18, 6), nullable=True)
    prod_qty_in_order_unit = db.Column(db.Numeric(18, 6), nullable=True)
    order_status = db.Column(db.String(4), nullable=True)
    cs_model = db.Column(db.String(18), nullable=True)
    cs_qty = db.Column(db.String(18), nullable=True)
    cs_lot_no = db.Column(db.String(18), nullable=True)
    cs_prod_date = db.Column(db.String(18), nullable=True)
    cs_exp_date = db.Column(db.String(18), nullable=True)
    cs_udi_di = db.Column(db.String(18), nullable=True)
    cs_udi_lotno = db.Column(db.String(18), nullable=True)
    cs_udi_prod = db.Column(db.String(18), nullable=True)
    cs_udi_serial = db.Column(db.String(18), nullable=True)

class Packing_Dtl(db.Model):
    __tablename__ = 'P_PACKING_DTL'
    __table_args__ = {'schema': 'dbo'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    m_box_no = db.Column(db.String(18), nullable=True)
    lot_no = db.Column(db.String(18), nullable=True)
    barcode = db.Column(db.String(20), nullable=True)
    udi_code = db.Column(db.String(40), nullable=True)
    packing_dt = db.Column(db.DateTime, nullable=True)
    exp_date = db.Column(db.DateTime, nullable=True)

class Biz_Partner(db.Model):
    __tablename__ = 'B_BIZ_PARTNER'
    __table_args__ = {'schema': 'dbo'}

    bp_cd = Column(db.String(8), primary_key=True)
    bp_nm = Column(db.String(20), nullable=True)
    bp_rgst_no = Column(db.String(20), nullable=True)
    nids_cd = Column(db.String(20), nullable=True)
    repre_nm = Column(db.String(20), nullable=True)
    phone_num = Column(db.String(20), nullable=True)
    zip_cd = Column(db.String(20), nullable=True)
    addr1 = Column(db.String(40), nullable=True)
    addr2 = Column(db.String(40), nullable=True)
    usage_flag = Column(db.String(2), nullable=True)
    insrt_dt = Column(db.DateTime, nullable=True)
    insrt_usr = Column(db.String(13), nullable=True)
    updt_dt = Column(db.DateTime, nullable=True)
    updt_usr = Column(db.String(13), nullable=True)
