from datetime import datetime

from flask import Blueprint, url_for, render_template, flash, request, session, g, app, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import redirect

from pybo import db
from pybo.forms import UserCreateForm, UserLoginForm, UserModifyForm, UserUpdateForm
from pybo.models import User
import functools

bp = Blueprint('basic', __name__, url_prefix='/basic')

@bp.route('/basic_product/', methods=('GET', 'POST'))
def basic_product():
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

    return render_template('basic/basic_product.html')

@bp.route('/basic_company/', methods=('GET', 'POST'))
def basic_company():
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

    return render_template('basic/basic_company.html')



