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
    Production_Barcode_Assign, Production_Results, kst_now, Packing_Hdr, Packing_Dtl, Storage_Location
from collections import defaultdict

bp = Blueprint('inventory', __name__, url_prefix='/inventory')

#재고조회
import logging

@bp.route('/inventory/', methods=['GET', 'POST'])
def inventory():
    form_submitted = False
    results = []

    if request.method == 'POST':
        form_submitted = True

        # Production_Results에서 REPORT_TYPE이 'G'인 레코드들의 제조오더번호(PRODT_ORDER_NO) 가져오기
        prodt_order_nos = db.session.query(Production_Results.PRODT_ORDER_NO).filter(
            Production_Results.REPORT_TYPE == 'G'
        ).distinct().all()

        # 제조오더번호 리스트를 가져옴
        prodt_order_nos = [order.PRODT_ORDER_NO for order in prodt_order_nos]

        # Production_Barcode_Assign에서 해당 제조오더번호에 대한 바코드와 작업센터(WC_CD) 가져오기
        barcode_assignments = db.session.query(
            Production_Barcode_Assign.barcode,
            Production_Barcode_Assign.WC_CD,
            Production_Barcode_Assign.PRODT_ORDER_NO
        ).filter(Production_Barcode_Assign.PRODT_ORDER_NO.in_(prodt_order_nos)).all()

        # 바코드 리스트 추출
        barcodes = [assignment.barcode for assignment in barcode_assignments]

        # Production_Barcode에서 해당 바코드들에 대한 product 정보 가져오기
        barcode_data = db.session.query(
            Production_Barcode.barcode,
            Production_Barcode.product
        ).filter(Production_Barcode.barcode.in_(barcodes)).all()

        # 제품 정보를 기준으로 Item에서 관련 품목 정보 가져오기
        product_to_item = defaultdict(list)
        for barcode, product in barcode_data:
            relevant_assignments = [
                assignment for assignment in barcode_assignments if assignment.barcode == barcode
            ]

            for assignment in relevant_assignments:
                wc_cd = assignment.WC_CD
                prodt_order_no = assignment.PRODT_ORDER_NO

                # Item 조회 조건 결정
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

                # Item에서 ALPHA_CODE와 조건에 맞는 항목 가져오기
                item = db.session.query(Item).filter(
                    Item.ALPHA_CODE == product,
                    Item.SPEC.contains(step_condition)
                ).first()

                # Production_Order에서 해당 PRODT_ORDER_NO의 SL_CD 조회
                production_order = db.session.query(
                    Production_Order.SL_CD
                ).filter(
                    Production_Order.PRODT_ORDER_NO == prodt_order_no
                ).first()

                # Storage_Location에서 SL_CD에 해당하는 SL_NM 조회
                sl_nm = None
                if production_order:
                    storage_location = db.session.query(Storage_Location).filter(
                        Storage_Location.SL_CD == production_order.SL_CD
                    ).first()
                    if storage_location:
                        sl_nm = storage_location.SL_NM

                if item and production_order:
                    # 결과를 저장
                    product_to_item[barcode].append({
                        'item_cd': item.ITEM_CD,
                        'item_nm': item.ITEM_NM,
                        'basic_unit': item.BASIC_UNIT,
                        'wc_cd': wc_cd,
                        'prodt_order_no': prodt_order_no,
                        'sl_cd': production_order.SL_CD,
                        'sl_nm': sl_nm  # SL_NM 추가
                    })

        # 최종 결과 리스트 생성
        results = [
            {
                'barcode': barcode,
                'item_cd': data['item_cd'],
                'item_nm': data['item_nm'],
                'basic_unit': data['basic_unit'],
                'wc_cd': data['wc_cd'],
                'prodt_order_no': data['prodt_order_no'],
                'sl_cd': data['sl_cd'],
                'sl_nm': data['sl_nm']  # SL_NM 추가
            }
            for barcode, data_list in product_to_item.items() for data in data_list
        ]

    return render_template('inventory/inventory.html', show_navigation_bar=True, results=results, form_submitted=form_submitted)




