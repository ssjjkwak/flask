import logging
import os
from datetime import datetime
from flask import Blueprint, url_for, render_template, flash, request, session, g, app, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import redirect
import pandas as pd
from werkzeug.utils import secure_filename
from pybo import db
from pybo.forms import UserCreateForm, UserLoginForm, UserModifyForm, UserUpdateForm
from pybo.models import User, Production_Order, Item, Work_Center, Plant, Bom, Production_Alpha
import functools

bp = Blueprint('product', __name__, url_prefix='/product')

ALLOWED_EXTENSIONS = {'xls', 'xlsx'}

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

@bp.route('/get_bom_data')
def get_bom_data():
    order_no = request.args.get('order_no')
    item_cd = request.args.get('item_cd')

    # 필요한 데이터 조회 로직
    bom_data = db.session.query(Bom, Item).join(Item, Bom.CHILD_ITEM_CD == Item.ITEM_CD).filter(Bom.PRNT_ITEM_CD == item_cd).all()

    results = []
    for bom, item in bom_data:
        results.append({
            'child_item_cd': bom.CHILD_ITEM_CD,
            'child_item_nm': item.ITEM_NM,
            'spec': item.SPEC,
            'child_item_unit': bom.CHILD_ITEM_UNIT,
            'child_item_qty': bom.CHILD_ITEM_QTY
        })

    return jsonify(results)

# 엑셀 업로드 / 엑셀 db 저장 / db 내용 보여주기
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/upload_excel', methods=['POST'])
def upload_excel():
    if 'excelFile' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['excelFile']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        process_excel(filepath)
        flash('File successfully uploaded and processed')
        return redirect(url_for('product.product_register'))
    else:
        flash('Allowed file types are xls, xlsx')
        return redirect(request.url)

def process_excel(filepath):
    df = pd.read_excel(filepath)
    for index, row in df.iterrows():
        barcode = row.get('barcode')
        modified = row.get('modified')
        if pd.isna(barcode) or pd.isna(modified):
            continue  # Skip rows without barcode or modified

        # Convert NaT to None and Timestamps to datetime
        def convert_value(value):
            if pd.isna(value):
                return None
            if isinstance(value, pd.Timestamp):
                return value.to_pydatetime()
            return value

        existing_record = Production_Alpha.query.filter_by(barcode=barcode).first()
        if existing_record:
            if existing_record.modified != modified:
                existing_record.modified = convert_value(modified)
                existing_record.product = convert_value(row.get('product'))
                existing_record.err_code = convert_value(row.get('err_code'))
                existing_record.err_info = convert_value(row.get('err_info'))
                existing_record.print_time = convert_value(row.get('print_time'))
                existing_record.LOT = convert_value(row.get('LOT'))

                # Update other fields as needed
                existing_record.inweight_time = convert_value(row.get('inweight_time'))
                existing_record.inweight_cycles = convert_value(row.get('inweight_cycles'))
                existing_record.inweight_station = convert_value(row.get('inweight_station'))
                existing_record.inweight_result = convert_value(row.get('inweight_result'))
                existing_record.inweight_value = convert_value(row.get('inweight_value'))
                existing_record.leaktest_cycles = convert_value(row.get('leaktest_cycles'))
                existing_record.leaktest_entry = convert_value(row.get('leaktest_entry'))
                existing_record.leaktest_exit = convert_value(row.get('leaktest_exit'))
                existing_record.leaktest_station = convert_value(row.get('leaktest_station'))
                existing_record.leaktest_value = convert_value(row.get('leaktest_value'))
                existing_record.leaktest_ptest = convert_value(row.get('leaktest_ptest'))
                existing_record.leaktest_duration = convert_value(row.get('leaktest_duration'))
                existing_record.leaktest_result = convert_value(row.get('leaktest_result'))
                existing_record.outweight_time = convert_value(row.get('outweight_time'))
                existing_record.outweight_station = convert_value(row.get('outweight_station'))
                existing_record.outweight_cycles = convert_value(row.get('outweight_cycles'))
                existing_record.outweight_result = convert_value(row.get('outweight_result'))
                existing_record.outweight_value = convert_value(row.get('outweight_value'))
                existing_record.itest2_time = convert_value(row.get('itest2_time'))
                existing_record.itest2_station = convert_value(row.get('itest2_station'))
                existing_record.itest2_cycles = convert_value(row.get('itest2_cycles'))
                existing_record.itest2_result = convert_value(row.get('itest2_result'))
                existing_record.itest2_value = convert_value(row.get('itest2_value'))
                existing_record.itest2_ptest = convert_value(row.get('itest2_ptest'))
                existing_record.prodlabel_time = convert_value(row.get('prodlabel_time'))
                existing_record.prodlabel_cycles = convert_value(row.get('prodlabel_cycles'))

                db.session.commit()
        else:
            p_production_alpha = Production_Alpha(
                LOT=convert_value(row.get('LOT')),
                product=convert_value(row.get('product')),
                barcode=barcode,
                modified=convert_value(modified),
                err_code=convert_value(row.get('err_code')),
                err_info=convert_value(row.get('err_info')),
                print_time=convert_value(row.get('print_time')),
                inweight_time=convert_value(row.get('inweight_time')),
                inweight_cycles=convert_value(row.get('inweight_cycles')),
                inweight_station=convert_value(row.get('inweight_station')),
                inweight_result=convert_value(row.get('inweight_result')),
                inweight_value=convert_value(row.get('inweight_value')),
                leaktest_cycles=convert_value(row.get('leaktest_cycles')),
                leaktest_entry=convert_value(row.get('leaktest_entry')),
                leaktest_exit=convert_value(row.get('leaktest_exit')),
                leaktest_station=convert_value(row.get('leaktest_station')),
                leaktest_value=convert_value(row.get('leaktest_value')),
                leaktest_ptest=convert_value(row.get('leaktest_ptest')),
                leaktest_duration=convert_value(row.get('leaktest_duration')),
                leaktest_result=convert_value(row.get('leaktest_result')),
                outweight_time=convert_value(row.get('outweight_time')),
                outweight_station=convert_value(row.get('outweight_station')),
                outweight_cycles=convert_value(row.get('outweight_cycles')),
                outweight_result=convert_value(row.get('outweight_result')),
                outweight_value=convert_value(row.get('outweight_value')),
                itest2_time=convert_value(row.get('itest2_time')),
                itest2_station=convert_value(row.get('itest2_station')),
                itest2_cycles=convert_value(row.get('itest2_cycles')),
                itest2_result=convert_value(row.get('itest2_result')),
                itest2_value=convert_value(row.get('itest2_value')),
                itest2_ptest=convert_value(row.get('itest2_ptest')),
                prodlabel_time=convert_value(row.get('prodlabel_time')),
                prodlabel_cycles=convert_value(row.get('prodlabel_cycles'))
            )
            db.session.add(p_production_alpha)
    db.session.commit()

@bp.route('/register/', methods=['GET', 'POST'])
def product_register():
    data = Production_Alpha.query.all()
    return render_template('product/product_register.html', data=data)

@bp.route('/register_result/', methods=['GET', 'POST'])
def product_register_result():
    data = Production_Alpha.query.all()
    return render_template('product/product_register_result.html', data=data)
