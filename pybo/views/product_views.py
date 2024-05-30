import logging
from datetime import datetime

from flask import Blueprint, url_for, render_template, flash, request, session, g, app, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import redirect

from pybo import db
from pybo.forms import UserCreateForm, UserLoginForm, UserModifyForm, UserUpdateForm
from pybo.models import User, Production_Order, Item, Work_Center, Plant
import functools

bp = Blueprint('product', __name__, url_prefix='/product')

@bp.route('/product_order/', methods=('GET', 'POST'))
def product_order():

    PLANT_CD = request.form.get('plant_code', '')
    WC_CD = request.form.get('wc_cd', '')
    ITEM_CD = request.form.get('item_cd', '')
    PLANT_START_DT = request.form.get('start_date', '')
    PLANT_COMPT_DT = request.form.get('complite_date', '')
    PRODT_ORDER_NO = request.form.get('prodt_order_no', '')


    if PLANT_START_DT:
        PLANT_START_DT = datetime.strptime(PLANT_START_DT, '%Y-%m-%d')
    else:
        PLANT_START_DT = None

    if PLANT_COMPT_DT:
        PLANT_COMPT_DT = datetime.strptime(PLANT_COMPT_DT, '%Y-%m-%d')
    else:
        PLANT_COMPT_DT = None

    plants = db.session.query(Plant).all()
    work_centers = db.session.query(Work_Center).all()
    items = db.session.query(Item).all()


    # Production_Order와 Item 조인 쿼리
    query_item = db.session.query(Production_Order, Item).join(
        Item, Production_Order.ITEM_CD == Item.ITEM_CD
    )

    if PLANT_CD:
        query_item = query_item.filter(Production_Order.PLANT_CD == PLANT_CD)
    if WC_CD:
        query_item = query_item.filter(Production_Order.WC_CD == WC_CD)
    if ITEM_CD:
        query_item = query_item.filter(Production_Order.ITEM_CD == ITEM_CD)
    if PLANT_START_DT:
        query_item = query_item.filter(Production_Order.PLANT_START_DT >= PLANT_START_DT)
    if PLANT_COMPT_DT:
        query_item = query_item.filter(Production_Order.PLANT_COMPT_DT <= PLANT_COMPT_DT)
    if PRODT_ORDER_NO:
        query_item = query_item.filter(Production_Order.PRODT_ORDER_NO == PRODT_ORDER_NO)

    orders_with_items = query_item.all()

    # Production_Order와 Work_Center 조인 쿼리
    query_wc = db.session.query(Production_Order, Work_Center).join(
        Work_Center, Production_Order.WC_CD == Work_Center.WC_CD
    )

    if PLANT_CD:
        query_wc = query_wc.filter(Production_Order.PLANT_CD == PLANT_CD)
    if WC_CD:
        query_wc = query_wc.filter(Production_Order.WC_CD == WC_CD)
    if ITEM_CD:
        query_wc = query_wc.filter(Production_Order.ITEM_CD == ITEM_CD)
    if PLANT_START_DT:
        query_wc = query_wc.filter(Production_Order.PLANT_START_DT >= PLANT_START_DT)
    if PLANT_COMPT_DT:
        query_wc = query_wc.filter(Production_Order.PLANT_COMPT_DT <= PLANT_COMPT_DT)
    if PRODT_ORDER_NO:
        query_wc = query_wc.filter(Production_Order.PRODT_ORDER_NO == PRODT_ORDER_NO)

    orders_with_wcs = query_wc.all()


    return render_template('product/product_order.html',
                           orders_with_items=orders_with_items,
                           orders_with_wcs=orders_with_wcs,
                           plants=plants,
                           work_centers=work_centers,
                           items=items,
                           PLANT_CD=PLANT_CD, WC_CD=WC_CD, ITEM_CD=ITEM_CD, PLANT_START_DT=PLANT_START_DT,
                           PRODT_ORDER_NO=PRODT_ORDER_NO, PLANT_COMPT_DT=PLANT_COMPT_DT)







