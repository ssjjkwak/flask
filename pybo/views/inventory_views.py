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
    Production_Barcode_Assign, Production_Results, kst_now, Packing_Hdr, Packing_Dtl, Storage_Location
from collections import defaultdict
from sqlalchemy.orm import aliased

bp = Blueprint('inventory', __name__, url_prefix='/inventory')

#재고조회
from sqlalchemy.orm import aliased
from sqlalchemy import func
from collections import defaultdict

@bp.route('/inventory/', methods=['GET', 'POST'])
def inventory():
    form_submitted = False
    results = []
    po_status = request.form.get('po_status')  # 체크박스 상태 확인

    if request.method == 'POST':
        form_submitted = True

        if po_status == 'none':  # 체크박스가 체크된 경우
            # 바코드 단위로 조회, 각 개별 row가 수량 1을 의미
            prodt_order_nos = db.session.query(Production_Results.PRODT_ORDER_NO).filter(
                Production_Results.REPORT_TYPE == 'G'
            ).distinct().all()

            prodt_order_nos = [order.PRODT_ORDER_NO for order in prodt_order_nos]

            barcode_assignments = db.session.query(
                Production_Barcode_Assign.barcode,
                Production_Barcode_Assign.WC_CD,
                Production_Barcode_Assign.PRODT_ORDER_NO
            ).filter(Production_Barcode_Assign.PRODT_ORDER_NO.in_(prodt_order_nos)).all()

            barcodes = [assignment.barcode for assignment in barcode_assignments]

            barcode_data = db.session.query(
                Production_Barcode.barcode,
                Production_Barcode.product
            ).filter(Production_Barcode.barcode.in_(barcodes)).all()

            product_to_item = defaultdict(list)
            for barcode, product in barcode_data:
                relevant_assignments = [
                    assignment for assignment in barcode_assignments if assignment.barcode == barcode
                ]

                for assignment in relevant_assignments:
                    wc_cd = assignment.WC_CD
                    prodt_order_no = assignment.PRODT_ORDER_NO

                    step_condition = ""
                    if wc_cd:
                        if wc_cd == 'WSF10':
                            step_condition = "10Step"
                        elif wc_cd == 'WSF30':
                            step_condition = "30Step"
                        elif wc_cd == 'WSF40':
                            step_condition = "40Step"
                        elif wc_cd == 'WSF50':
                            step_condition = "50Step"
                        elif wc_cd == 'WSF60':
                            step_condition = "60Step"
                        elif wc_cd == 'WSF70':
                            step_condition = "70Step"

                    item = db.session.query(Item).filter(
                        Item.ALPHA_CODE == product,
                        Item.SPEC.contains(step_condition)
                    ).first()

                    production_order = db.session.query(
                        Production_Order.SL_CD
                    ).filter(
                        Production_Order.PRODT_ORDER_NO == prodt_order_no
                    ).first()

                    sl_nm = None
                    if production_order:
                        storage_location = db.session.query(Storage_Location).filter(
                            Storage_Location.SL_CD == production_order.SL_CD
                        ).first()
                        if storage_location:
                            sl_nm = storage_location.SL_NM

                    if item and production_order:
                        product_to_item[barcode].append({
                            'item_cd': item.ITEM_CD,
                            'item_nm': item.ITEM_NM,
                            'basic_unit': item.BASIC_UNIT,
                            'wc_cd': wc_cd,
                            'prodt_order_no': prodt_order_no,
                            'sl_cd': production_order.SL_CD,
                            'sl_nm': sl_nm
                        })

            results = [
                {
                    'barcode': barcode,
                    'item_cd': data['item_cd'],
                    'item_nm': data['item_nm'],
                    'basic_unit': data['basic_unit'],
                    'wc_cd': data['wc_cd'],
                    'prodt_order_no': data['prodt_order_no'],
                    'sl_cd': data['sl_cd'],
                    'sl_nm': data['sl_nm']
                }
                for barcode, data_list in product_to_item.items() for data in data_list
            ]

        else:
            # 체크박스가 선택되지 않은 경우 품목별 총 재고 수량 집계하여 조회
            results = (
                db.session.query(
                    Item.ITEM_CD.label("item_cd"),
                    Item.ITEM_NM.label("item_nm"),
                    Item.BASIC_UNIT.label("basic_unit"),
                    func.count(Production_Barcode_Assign.barcode).label("total_qty")  # 품목별 바코드 개수 집계
                )
                .join(Production_Results, Production_Results.PRODT_ORDER_NO == Production_Barcode_Assign.PRODT_ORDER_NO)
                .join(Production_Barcode, Production_Barcode.barcode == Production_Barcode_Assign.barcode)
                .join(Item, Item.ALPHA_CODE == Production_Barcode.product)
                .filter(Production_Results.REPORT_TYPE == 'G')  # 실적 데이터 기준
                .group_by(Item.ITEM_CD, Item.ITEM_NM, Item.BASIC_UNIT)
                .all()
            )

            results = [
                {
                    'item_cd': item.item_cd,
                    'item_nm': item.item_nm,
                    'basic_unit': item.basic_unit,
                    'total_qty': item.total_qty
                }
                for item in results
            ]

    return render_template('inventory/inventory.html', show_navigation_bar=True, results=results,
                           form_submitted=form_submitted, po_status=po_status)













