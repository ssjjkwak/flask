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

#품목정보조회
@bp.route('/item/', methods=['GET', 'POST'])
def item():

    return render_template('masterdata/item.html', show_navigation_bar=True)

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