from datetime import datetime

from flask import Blueprint, url_for, render_template, flash, request, session, g, app, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import redirect

from pybo import db
from pybo.forms import UserCreateForm, UserLoginForm, UserModifyForm, UserUpdateForm
from pybo.models import Users, Roles, Users_Roles, ProductionOrderHeader, ProductionResults
import functools

bp = Blueprint('delivery', __name__, url_prefix='/delivery')

@bp.route('/delivery_select/', methods=('GET', 'POST'))
def delivery_select():
    # start_date = datetime.strptime('2024-01-04', '%Y-%m-%d')
    # end_date = datetime.strptime('2024-05-14', '%Y-%m-%d')
    # plant_code = 'P710'
    #
    # orders = db.session.query(ProductionOrderHeader, ProductionResults). \
    #     outerjoin(ProductionResults, ProductionOrderHeader.prodt_order_no == ProductionResults.prodt_order_no). \
    #     filter(ProductionOrderHeader.plan_start_dt >= start_date,
    #            ProductionOrderHeader.plan_start_dt <= end_date,
    #            ProductionOrderHeader.plant_cd == plant_code). \
    #     all()

    return render_template('delivery/delivery_select.html')

# @bp.route('/data', methods=['GET','POST'])
# def receive_data():
#     if request.method == 'POST':
#         # POST 요청 처리
#         return jsonify(success=True)
#     else:
#         # GET 요청에 대한 응답
#         return 'This endpoint is reachable.'

@bp.route('/delivery_UDIselect/', methods=('GET', 'POST'))
def delivery_UDIselect():
    # start_date = datetime.strptime('2024-01-04', '%Y-%m-%d')
    # end_date = datetime.strptime('2024-05-14', '%Y-%m-%d')
    # plant_code = 'P710'
    #
    # orders = db.session.query(ProductionOrderHeader, ProductionResults). \
    #     outerjoin(ProductionResults, ProductionOrderHeader.prodt_order_no == ProductionResults.prodt_order_no). \
    #     filter(ProductionOrderHeader.plan_start_dt >= start_date,
    #            ProductionOrderHeader.plan_start_dt <= end_date,
    #            ProductionOrderHeader.plant_cd == plant_code). \
    #     all()

    return render_template('delivery/delivery_UDIselect.html')

