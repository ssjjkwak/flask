import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import win32com.client
from flask import Blueprint, url_for, render_template, request, current_app, jsonify, g, flash
from sqlalchemy import null, func
from werkzeug.utils import redirect, secure_filename
import pandas as pd
from pybo import db
from pybo.models import Production_Order, Item, Work_Center, Plant, Production_Alpha, Production_Barcode, \
    Barcode_Flow, Production_Results, kst_now, Packing_Hdr, Packing_Dtl, Sales_Order, Biz_Partner
from collections import defaultdict

bp = Blueprint('sales', __name__, url_prefix='/sales')

@bp.route('/sales_order/', methods=['GET', 'POST'])
def sales_order():
    form_submitted = False
    BP_CD = ''
    SO_NO = ''
    SO_SEQ = ''
    PLANT_CD = ''
    SL_CD = ''
    ITEM_CD = ''
    SO_QTY = ''
    SO_PRICE = ''
    NET_AMT = ''
    SO_DT_START = datetime.today().strftime('%Y-%m-%d')  # 오늘 날짜
    SO_DT_END = (datetime.today() + timedelta(days=30)).strftime('%Y-%m-%d')  # 30일 후 날짜
    REQ_DLVY_DT_START = datetime.today().strftime('%Y-%m-%d')  # 오늘 날짜
    REQ_DLVY_DT_END = (datetime.today() + timedelta(days=365)).strftime('%Y-%m-%d')  # 30일 후 날짜
    CUST_PO_NO = ''

    # 기본 Sales_Order 쿼리에 Biz_Partner와 Item 조인을 추가
    sales_order_query = db.session.query(Sales_Order, Biz_Partner.bp_nm, Item.ITEM_NM, Item.SPEC, Item.BASIC_UNIT).\
        join(Biz_Partner, Sales_Order.BP_CD == Biz_Partner.bp_cd, isouter=True).\
        join(Item, Sales_Order.ITEM_CD == Item.ITEM_CD, isouter=True)

    if request.method == 'POST':
        form_submitted = True
        BP_CD = request.form.get('bp_cd', '')
        SO_NO = request.form.get('so_no', '')
        SO_SEQ = request.form.get('so_seq', '')
        PLANT_CD = request.form.get('plant_cd', '')
        SL_CD = request.form.get('sl_cd', '')
        ITEM_CD = request.form.get('item_cd', '')
        SO_QTY = request.form.get('so_qty', '')
        SO_PRICE = request.form.get('so_price', '')
        NET_AMT = request.form.get('net_amt', '')
        SO_DT_START = request.form.get('so_dt_start', SO_DT_START)  # POST 시에도 기본값을 유지
        SO_DT_END = request.form.get('so_dt_end', SO_DT_END)  # POST 시에도 기본값을 유지
        REQ_DLVY_DT_START = request.form.get('req_dlvy_dt_start', REQ_DLVY_DT_START)  # 기본값 유지
        REQ_DLVY_DT_END = request.form.get('req_dlvy_dt_end', REQ_DLVY_DT_END)  # 기본값 유지
        CUST_PO_NO = request.form.get('cust_po_no', '')

        # 필터링 조건 적용
        if BP_CD:
            sales_order_query = sales_order_query.filter(Sales_Order.BP_CD.like(f'%{BP_CD}%'))
        if SO_NO:
            sales_order_query = sales_order_query.filter(Sales_Order.SO_NO.like(f'%{SO_NO}%'))
        if ITEM_CD:
            sales_order_query = sales_order_query.filter(Sales_Order.ITEM_CD.like(f'%{ITEM_CD}%'))
        if SO_DT_START and SO_DT_END:
            sales_order_query = sales_order_query.filter(Sales_Order.SO_DT.between(SO_DT_START, SO_DT_END))
        if REQ_DLVY_DT_START and REQ_DLVY_DT_END:
            sales_order_query = sales_order_query.filter(Sales_Order.REQ_DLVY_DT.between(REQ_DLVY_DT_START, REQ_DLVY_DT_END))
        if CUST_PO_NO:
            sales_order_query = sales_order_query.filter(Sales_Order.CUST_PO_NO.like(f'%{CUST_PO_NO}%'))

    # 쿼리 실행
    sales_orders = sales_order_query.all()


    return render_template('sales/sales_order.html',
                           sales_orders=sales_orders,
                           form_submitted=form_submitted,
                           BP_CD=BP_CD,
                           SO_NO=SO_NO,
                           ITEM_CD=ITEM_CD,
                           SO_QTY=SO_QTY,
                           SO_PRICE=SO_PRICE,
                           NET_AMT=NET_AMT,
                           SO_SEQ=SO_SEQ,
                           PLANT_CD=PLANT_CD,
                           SL_CD=SL_CD,
                           SO_DT_START=SO_DT_START,
                           SO_DT_END=SO_DT_END,
                           REQ_DLVY_DT_START=REQ_DLVY_DT_START,
                           REQ_DLVY_DT_END=REQ_DLVY_DT_END,
                           CUST_PO_NO=CUST_PO_NO)




@bp.route('/supply_details/', methods=['GET'])
def supply_details():

    return render_template('sales/supply_details.html',  show_navigation_bar=True)