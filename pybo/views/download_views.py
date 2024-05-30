from datetime import datetime
from io import BytesIO

import pandas as pd
from flask import Blueprint, url_for, render_template, flash, request, session, g, app, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import redirect

from pybo import db
from pybo.forms import UserCreateForm, UserLoginForm, UserModifyForm, UserUpdateForm
from pybo.models import User
import functools

bp = Blueprint('download', __name__, url_prefix='/download')


def convert_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output


@bp.route('/download/user_manage')
def download_user_manage():
    users_with_roles = db.session.query(Users, Roles.rolename) \
        .select_from(Users) \
        .join(Users_Roles, Users.users_id == Users_Roles.users_id) \
        .join(Roles, Users_Roles.roles_id == Roles.roles_id) \
        .all()
    data = {'Index': [user.users_id for user, rolename in users_with_roles],
            '사용자ID': [user.username for user, rolename in users_with_roles],
            '성명':[user.name for user, rolename in users_with_roles],
            '이메일':[user.email for user, rolename in users_with_roles],
            '부서':[user.department for user, rolename in users_with_roles],
            '직위/직책':[user.jobtitle for user, rolename in users_with_roles],
            '권한':[rolename for user, rolename in users_with_roles],
            '전화번호':[user.phonenumber for user, rolename in users_with_roles]
            }
    df = pd.DataFrame(data)
    excel_file = convert_to_excel(df)

    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='user_manage_data.xlsx'
    )

@bp.route('/download/product_order')
def download_product_order():
    # users_with_roles = db.session.query(Users, Roles.rolename) \
    #     .select_from(Users) \
    #     .join(Users_Roles, Users.users_id == Users_Roles.users_id) \
    #     .join(Roles, Users_Roles.roles_id == Roles.roles_id) \
    #     .all()
    # ERP 데이터를 가져오게 되면 해당 데이터를 select하는 쿼리 작성

    data = {'제조 오더 번호': ['PD20240122000001','PD20240122000002','PD20240122000003','PD20240122000004','PD20240122000005','PD20240122000006','PD20240122000007','PD20240122000008','PD20240122000009','PD20240122000010','PD20240122000011','PD20240122000012'],
            '공장 코드': ['p710','p710','p710','p710','p710','p710','p710','p710','p710','p710','p710','p710'],
            '품목 코드':['BES0A02-020','BES0A02-020','BES0A02-020','BES0A02-020','BES0A02-020','BES0A02-020','BES0A02-020','BES0A02-020','BES0A02-020','BES0A02-020','BES0A02-020','BES0A02-020'],
            '계획 시작 날짜':['2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19'],
            '계획 완료 날짜':['2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19'],
            '주문 수량(기본 단위)':['340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000'],
            '생산 수량(주문 단위)':['340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000'],
            '단위': ['MT','MT','MT','MT','MT','MT','MT','MT','MT','MT','MT','MT'],
            '주문 상태': ['close','close','close','close','close','close','close','close','close','close','close','close'],
            '수령 수량(실적)':['340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000'],
            '수령 수량(양품)': ['300.000','300.000','300.000','300.000','300.000','300.000','300.000','300.000','300.000','300.000','300.000','300.000'],
            '수령 수량(불량)': ['40.000','40.000','40.000','40.000','40.000','40.000','40.000','40.000','40.000','40.000','40.000','40.000'],
            '수령 플래그': ['N','N','N','N','N','N','N','N','N','N','N','N']
            }
    df = pd.DataFrame(data)
    excel_file = convert_to_excel(df)

    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='product_order_data.xlsx'
    )



@bp.route('/download/delivery_select')
def download_delivery_select():
    # users_with_roles = db.session.query(Users, Roles.rolename) \
    #     .select_from(Users) \
    #     .join(Users_Roles, Users.users_id == Users_Roles.users_id) \
    #     .join(Roles, Users_Roles.roles_id == Roles.roles_id) \
    #     .all()
    # ERP 데이터를 가져오게 되면 해당 데이터를 select하는 쿼리 작성

    data = {'제조 오더 번호': ['PD20240122000001','PD20240122000002','PD20240122000003','PD20240122000004','PD20240122000005','PD20240122000006','PD20240122000007','PD20240122000008','PD20240122000009','PD20240122000010','PD20240122000011','PD20240122000012'],
            '공장 코드': ['p710','p710','p710','p710','p710','p710','p710','p710','p710','p710','p710','p710'],
            '품목 코드':['BES0A02-020','BES0A02-020','BES0A02-020','BES0A02-020','BES0A02-020','BES0A02-020','BES0A02-020','BES0A02-020','BES0A02-020','BES0A02-020','BES0A02-020','BES0A02-020'],
            '계획 시작 날짜':['2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19'],
            '계획 완료 날짜':['2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19','2024-01-19'],
            '주문 수량(기본 단위)':['340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000'],
            '생산 수량(주문 단위)':['340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000'],
            '단위': ['MT','MT','MT','MT','MT','MT','MT','MT','MT','MT','MT','MT'],
            '주문 상태': ['close','close','close','close','close','close','close','close','close','close','close','close'],
            '수령 수량(실적)':['340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000','340.000'],
            '수령 수량(양품)': ['300.000','300.000','300.000','300.000','300.000','300.000','300.000','300.000','300.000','300.000','300.000','300.000'],
            '수령 수량(불량)': ['40.000','40.000','40.000','40.000','40.000','40.000','40.000','40.000','40.000','40.000','40.000','40.000'],
            '수령 플래그': ['N','N','N','N','N','N','N','N','N','N','N','N']
            }
    df = pd.DataFrame(data)
    excel_file = convert_to_excel(df)

    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='delivery_select_data.xlsx'
    )