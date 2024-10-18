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
    Production_Barcode_Assign, Production_Results, kst_now, Packing_Hdr, Packing_Dtl
from collections import defaultdict

bp = Blueprint('masterdata', __name__, url_prefix='/masterdata')

# 품목정보조회
@bp.route('/item/', methods=['GET', 'POST'])
def item():
    form_submitted = False
    PLANT_CD = ''
    ITEM_CD = ''
    ITEM_GROUP_CD = ''
    UDI_CODE = ''

    # 모든 공장 목록을 조회하여 화면에 표시
    plants = db.session.query(Plant).all()
    items_query = db.session.query(Item)

    if request.method == 'POST':
        form_submitted = True
        # 입력된 조회 조건을 가져옴
        PLANT_CD = request.form.get('plant_code', '')
        ITEM_CD = request.form.get('item_cd', '')
        ITEM_GROUP_CD = request.form.get('item_group_cd', '')
        UDI_CODE = request.form.get('udi_code', '')

        # 필터링 조건을 적용
        if PLANT_CD:
            items_query = items_query.filter(Item.PLANT_CD == PLANT_CD)
        if ITEM_CD:
            items_query = items_query.filter(Item.ITEM_CD.like(f'%{ITEM_CD}%'))
        if ITEM_GROUP_CD:
            items_query = items_query.filter(Item.ITEM_GROUP_CD.like(f'%{ITEM_GROUP_CD}%'))
        if UDI_CODE:
            items_query = items_query.filter(Item.UDI_CODE.like(f'%{UDI_CODE}%'))

    # 조회 결과 가져오기
    items = items_query.all()

    return render_template('masterdata/item.html',
                           plants=plants,
                           items=items,
                           PLANT_CD=PLANT_CD,
                           ITEM_CD=ITEM_CD,
                           ITEM_GROUP_CD=ITEM_GROUP_CD,
                           UDI_CODE=UDI_CODE,
                           form_submitted=form_submitted)


#BOM정보조회
@bp.route('/bom/', methods=['GET'])
def bom():
    # 데이터베이스에서 BOM 데이터 조회
    bom_items = db.session.query(Bom).all()

    # 데이터 계층화
    tree_data = {}
    for item in bom_items:
        parent_id = item.PRNT_ITEM_CD or 'root'
        item_name = item.child_item.ITEM_NM if item.child_item else f"Unknown {item.CHILD_ITEM_CD}"

        if parent_id not in tree_data:
            tree_data[parent_id] = []
        tree_data[parent_id].append({
            "id": item.CHILD_ITEM_CD,
            "text": item_name
        })

    return render_template('masterdata/bom.html', tree_data=tree_data)



#거래처정보조회
@bp.route('/vendor/', methods=['GET', 'POST'])
def vendor():

    return render_template('masterdata/vendor.html', show_navigation_bar=True)