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
from pybo.models import Production_Order, Item, Work_Center, Plant, Bom, Production_Alpha, Production_Barcode, \
    Production_Barcode_Assign, Production_Results, kst_now, Packing_Hdr, Packing_Dtl, Sales_Order
from collections import defaultdict

bp = Blueprint('sales', __name__, url_prefix='/sales')

@bp.route('/sales_order/', methods=['GET'])
def sales_order():
    form_submitted = False
    bp_cd = ''
    so_no = ''
    item_cd = ''
    so_dt = ''
    req_dlvy_dt = ''
    cust_po_no = ''

    sales_order_query = db.session.query(Sales_Order)

    if request.method == 'POST':
        form_submitted = True
        bp_cd = request.form.get('bp_cd', '')
        so_no = request.form.get('so_no', '')
        item_cd = request.form.get('item_cd', '')
        so_dt = request.form.get('so_dt', '')
        req_dlvy_dt = request.form.get('req_dlvy_dt', '')
        cust_po_no = request.form.get('cust_po_no', '')

        # 필터링 조건 적용
        if bp_cd:
            sales_order_query = sales_order_query.filter(Sales_Order.bp_cd.like(f'%{bp_cd}%'))
        if so_no:
            sales_order_query = sales_order_query.filter(Sales_Order.so_no.like(f'%{so_no}%'))
        if item_cd:
            sales_order_query = sales_order_query.filter(Sales_Order.item_cd.like(f'%{item_cd}%'))

    sales_orders = sales_order_query.all()

    return render_template('sales/sales_order.html',
                           sales_orders=sales_orders,
                           form_submitted=form_submitted,
                           bp_cd=bp_cd,
                           so_no=so_no,
                           item_cd=item_cd,
                           so_dt=so_dt,
                           req_dlvy_dt=req_dlvy_dt,
                           cust_po_no=cust_po_no)

@bp.route('/supply_details/', methods=['GET'])
def supply_details():

    return render_template('sales/supply_details.html',  show_navigation_bar=True)