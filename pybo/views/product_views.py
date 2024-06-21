import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from flask import Blueprint, url_for, render_template, request, current_app, jsonify
from sqlalchemy import null
from werkzeug.utils import redirect, secure_filename
import pandas as pd
from pybo import db
from pybo.models import Production_Order, Item, Work_Center, Plant, Bom, Production_Alpha, Production_Barcode, \
    Production_Barcode_Assign, Production_Results, kst_now

bp = Blueprint('product', __name__, url_prefix='/product')

ALLOWED_EXTENSIONS = {'xls', 'xlsx'}


@bp.route('/product_order/', methods=('GET', 'POST'))
def product_order():
    orders_with_items = []
    orders_with_wcs = []
    form_submitted = False
    PLANT_CD = ''
    WC_CD = ''
    ITEM_CD = ''
    PLANT_START_DT = None
    PLANT_COMPT_DT = None
    PRODT_ORDER_NO = ''

    plants = db.session.query(Plant).all()

    if request.method == 'POST':
        form_submitted = True
        PLANT_CD = request.form.get('plant_code', '')
        WC_CD = request.form.get('wc_cd', '')
        ITEM_CD = request.form.get('item_cd', '')
        PLANT_START_DT = request.form.get('start_date', '')
        PLANT_COMPT_DT = request.form.get('end_date', '')
        PRODT_ORDER_NO = request.form.get('prodt_order_no', '')

        if PLANT_START_DT:
            PLANT_START_DT = datetime.strptime(PLANT_START_DT, '%Y-%m-%d')
        if PLANT_COMPT_DT:
            PLANT_COMPT_DT = datetime.strptime(PLANT_COMPT_DT, '%Y-%m-%d')
    else:

        if plants:
            PLANT_CD = plants[0].PLANT_CD

    if not PLANT_START_DT:
        PLANT_START_DT = datetime.today()
    if not PLANT_COMPT_DT:
        PLANT_COMPT_DT = datetime.today() + timedelta(days=30)

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

    work_centers = db.session.query(Work_Center).all()
    items = db.session.query(Item).all()

    return render_template('product/product_order.html',
                           orders_with_items=orders_with_items,
                           orders_with_wcs=orders_with_wcs,
                           plants=plants,
                           work_centers=work_centers,
                           items=items,
                           PLANT_CD=PLANT_CD, WC_CD=WC_CD, ITEM_CD=ITEM_CD, PLANT_START_DT=PLANT_START_DT,
                           PRODT_ORDER_NO=PRODT_ORDER_NO, PLANT_COMPT_DT=PLANT_COMPT_DT,
                           form_submitted=form_submitted)


@bp.route('/get_bom_data')
def get_bom_data():
    order_no = request.args.get('order_no')
    item_cd = request.args.get('item_cd')

    bom_data = db.session.query(Bom, Item).join(Item, Bom.CHILD_ITEM_CD == Item.ITEM_CD).filter(
        Bom.PRNT_ITEM_CD == item_cd).all()

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


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/upload_excel', methods=['POST'])
def upload_excel():
    if 'excelFile' not in request.files:
        return '<script>alert("No file part"); window.location.href="/product/register/";</script>'
    file = request.files['excelFile']
    if file.filename == '':
        return '<script>alert("No selected file"); window.location.href="/product/register/";</script>'
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        process_excel(filepath)
        return '<script>alert("Excel 파일 업로드 완료."); window.location.href="/product/register/";</script>'
    else:
        return '<script>alert("Allowed file types are xls, xlsx"); window.location.href="/product/register/";</script>'


def convert_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, float):
        return round(value, 2)  # 소수점 2자리까지 반올림
    if isinstance(value, int):
        return value
    return value


def process_excel(filepath):
    df = pd.read_excel(filepath)
    new_records = []
    update_records = []

    for index, row in df.iterrows():
        barcode = row.get('barcode')
        modified = row.get('modified')
        if pd.isna(barcode) or pd.isna(modified):
            continue

        existing_record = Production_Alpha.query.filter_by(barcode=barcode).first()
        record_data = {
            'LOT': convert_value(row.get('LOT')),
            'product': convert_value(row.get('product')),
            'barcode': barcode,
            'modified': convert_value(modified),
            'err_code': convert_value(row.get('err_code')),
            'err_info': convert_value(row.get('err_info')),
            'print_time': convert_value(row.get('print_time')),
            'inweight_time': convert_value(row.get('inweight_time')),
            'inweight_cycles': convert_value(row.get('inweight_cycles')),
            'inweight_station': convert_value(row.get('inweight_station')),
            'inweight_result': convert_value(row.get('inweight_result')),
            'inweight_value': convert_value(row.get('inweight_value')),
            'leaktest_cycles': convert_value(row.get('leaktest_cycles')),
            'leaktest_entry': convert_value(row.get('leaktest_entry')),
            'leaktest_exit': convert_value(row.get('leaktest_exit')),
            'leaktest_station': convert_value(row.get('leaktest_station')),
            'leaktest_value': convert_value(row.get('leaktest_value')),
            'leaktest_ptest': convert_value(row.get('leaktest_ptest')),
            'leaktest_duration': convert_value(row.get('leaktest_duration')),
            'leaktest_result': convert_value(row.get('leaktest_result')),
            'outweight_time': convert_value(row.get('outweight_time')),
            'outweight_station': convert_value(row.get('outweight_station')),
            'outweight_cycles': convert_value(row.get('outweight_cycles')),
            'outweight_result': convert_value(row.get('outweight_result')),
            'outweight_value': convert_value(row.get('outweight_value')),
            'itest2_time': convert_value(row.get('itest2_time')),
            'itest2_station': convert_value(row.get('itest2_station')),
            'itest2_cycles': convert_value(row.get('itest2_cycles')),
            'itest2_result': convert_value(row.get('itest2_result')),
            'itest2_value': convert_value(row.get('itest2_value')),
            'itest2_ptest': convert_value(row.get('itest2_ptest')),
            'prodlabel_time': convert_value(row.get('prodlabel_time')),
            'prodlabel_cycles': convert_value(row.get('prodlabel_cycles')),
            'INSRT_DT': convert_value(row.get('INSRT_DT')),
            'UPDT_DT': convert_value(row.get('UPDT_DT')),
            'REPORT_FLAG': convert_value(row.get('REPORT_FLAG'))
        }

        if existing_record:
            if existing_record.modified != modified:
                for key, value in record_data.items():
                    setattr(existing_record, key, value)
                update_records.append(existing_record)
        else:
            new_records.append(record_data)

    if new_records:
        db.session.bulk_insert_mappings(Production_Alpha, new_records)
    if update_records:
        db.session.bulk_update_mappings(Production_Alpha, [record.__dict__ for record in update_records])

    db.session.commit()


# 여기에 조회조건 걸어서 register 화면에 데이터 렌더링
@bp.route('/register/', methods=['GET', 'POST'])
def product_register():
    alpha_data = Production_Alpha.query.filter_by(REPORT_FLAG='N').all()
    return render_template('product/product_register.html', data=alpha_data)


@bp.route('/register_result/', methods=['GET', 'POST'])
def product_register_result():
    results = []
    form_submitted = False
    PLANT_CD = ''
    LOT_NO_START = ''
    LOT_NO_END = ''
    INSRT_DT_START = None
    INSRT_DT_END = None
    BARCODE_NO_START = ''
    BARCODE_NO_END = ''

    plants = db.session.query(Plant).all()

    if request.method == 'POST':
        form_submitted = True
        PLANT_CD = request.form.get('plant_code', '')
        LOT_NO_START = request.form.get('lot_no_start', '')
        LOT_NO_END = request.form.get('lot_no_end', '')
        INSRT_DT_START = request.form.get('start_date', '')
        INSRT_DT_END = request.form.get('end_date', '')
        BARCODE_NO_START = request.form.get('barcode_no_start', '')
        BARCODE_NO_END = request.form.get('barcode_no_end', '')

        if INSRT_DT_START:
            INSRT_DT_START = datetime.strptime(INSRT_DT_START, '%Y-%m-%d')
        if INSRT_DT_END:
            INSRT_DT_END = datetime.strptime(INSRT_DT_END, '%Y-%m-%d')

    if not INSRT_DT_START:
        INSRT_DT_START = datetime.today()
    if not INSRT_DT_END:
        INSRT_DT_END = datetime.today() + timedelta(days=30)

    query = db.session.query(
        Production_Barcode_Assign,
        Production_Alpha.LOT,
        Production_Alpha.product
    ).join(
        Production_Alpha, Production_Barcode_Assign.barcode == Production_Alpha.barcode
    )

    if LOT_NO_START and LOT_NO_END:
        query = query.filter(Production_Alpha.LOT.between(LOT_NO_START, LOT_NO_END))
    if INSRT_DT_START:
        query = query.filter(Production_Barcode_Assign.INSRT_DT >= INSRT_DT_START)
    if INSRT_DT_END:
        query = query.filter(Production_Barcode_Assign.INSRT_DT <= INSRT_DT_END)
    if BARCODE_NO_START and BARCODE_NO_END:
        query = query.filter(Production_Barcode_Assign.barcode.between(BARCODE_NO_START, BARCODE_NO_END))

    results = query.all()

    return render_template('product/product_register_result.html',
                           results=results,
                           plants=plants,
                           LOT_NO_START=LOT_NO_START,
                           LOT_NO_END=LOT_NO_END,
                           INSRT_DT_START=INSRT_DT_START,
                           INSRT_DT_END=INSRT_DT_END,
                           BARCODE_NO_START=BARCODE_NO_START,
                           BARCODE_NO_END=BARCODE_NO_END,
                           form_submitted=form_submitted)




def remove_microseconds(dt):
    """Remove microseconds from a datetime object."""
    if dt:
        return dt.replace(microsecond=0)
    return dt


def parse_datetime(datetime_str):
    """Parse datetime string with various formats including milliseconds."""
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f%z'):
        try:
            dt = datetime.strptime(datetime_str, fmt)
            return remove_microseconds(dt)
        except ValueError:
            continue
    raise ValueError(f'time data {datetime_str} does not match any known format')


@bp.route('/register', methods=['POST'])
def register():
    selected_records = request.form.getlist('chkRow')
    if not selected_records:
        return '<script>alert("실적 처리할 레코드를 선택해 주세요."); window.location.href="/product/register/";</script>'

    new_records = []
    updated_records = []

    for record_id in selected_records:
        barcode, modified_str = record_id.split('|')
        modified = parse_datetime(modified_str)

        processed_record = Production_Barcode.query.filter_by(barcode=barcode).first()
        if processed_record:
            continue

        record = Production_Alpha.query.filter_by(barcode=barcode).first()

        if record:
            processes = []
            if record.print_time is not None:
                processes.append('WSF10')
            if record.outweight_result == 1:
                processes.append('WSF30')
            if record.prodlabel_cycles == 1:
                processes.append('WSF60')

            for process in processes:
                existing_record = Production_Barcode.query.filter_by(barcode=record.barcode, wc_cd=process).first()
                if existing_record:
                    continue

                production_barcode = {
                    'LOT': record.LOT,
                    'product': record.product,
                    'barcode': record.barcode,
                    'wc_cd': process,
                    'err_code': record.err_code,
                    'err_info': record.err_info,
                    'print_time': convert_value(record.print_time),
                    'inweight_time': convert_value(record.inweight_time),
                    'inweight_cycles': convert_value(record.inweight_cycles),
                    'inweight_station': convert_value(record.inweight_station),
                    'inweight_result': convert_value(record.inweight_result),
                    'inweight_value': convert_value(record.inweight_value),
                    'leaktest_cycles': convert_value(record.leaktest_cycles),
                    'leaktest_entry': convert_value(record.leaktest_entry),
                    'leaktest_exit': convert_value(record.leaktest_exit),
                    'leaktest_station': convert_value(record.leaktest_station),
                    'leaktest_value': convert_value(record.leaktest_value),
                    'leaktest_ptest': convert_value(record.leaktest_ptest),
                    'leaktest_duration': convert_value(record.leaktest_duration),
                    'leaktest_result': convert_value(record.leaktest_result),
                    'outweight_time': convert_value(record.outweight_time),
                    'outweight_station': convert_value(record.outweight_station),
                    'outweight_cycles': convert_value(record.outweight_cycles),
                    'outweight_result': convert_value(record.outweight_result),
                    'outweight_value': convert_value(record.outweight_value),
                    'itest2_time': convert_value(record.itest2_time),
                    'itest2_station': convert_value(record.itest2_station),
                    'itest2_cycles': convert_value(record.itest2_cycles),
                    'itest2_result': convert_value(record.itest2_result),
                    'itest2_value': convert_value(record.itest2_value),
                    'itest2_ptest': convert_value(record.itest2_ptest),
                    'prodlabel_time': convert_value(record.prodlabel_time),
                    'prodlabel_cycles': convert_value(record.prodlabel_cycles),
                    'INSRT_DT': convert_value(record.INSRT_DT),
                    'INSRT_USR': record.INSRT_USR,
                    'UPDT_DT': convert_value(record.UPDT_DT),
                    'UPDT_USR': record.UPDT_USR
                }
                new_records.append(production_barcode)

            if len(processes) == 3:
                record.REPORT_FLAG = 'Y'
                updated_records.append(record)

    if new_records:
        db.session.bulk_insert_mappings(Production_Barcode, new_records)
    if updated_records:
        db.session.bulk_update_mappings(Production_Alpha, [record.__dict__ for record in updated_records])

    db.session.commit()

    assign_production_orders()

    return '<script>alert("실적 처리가 완료되었습니다."); window.location.href="/product/register/";</script>'


def assign_production_orders():
    barcodes = Production_Barcode.query.filter(Production_Barcode.REPORT_FLAG == 'N').all()
    orders = {wc_cd: [] for wc_cd in ['WSF10', 'WSF30', 'WSF60']}

    for wc_cd in orders.keys():
        orders[wc_cd] = Production_Order.query.filter_by(WC_CD=wc_cd).all()

    order_indices = {wc_cd: 0 for wc_cd in orders.keys()}
    assn_records = []
    updated_barcodes = []

    for barcode in barcodes:
        wc_cd = barcode.wc_cd
        if wc_cd in orders and orders[wc_cd]:
            order = orders[wc_cd][order_indices[wc_cd]]

            if wc_cd == 'WSF10' and barcode.print_time is None:
                report_type = 'B'
            elif wc_cd == 'WSF30' and barcode.outweight_result == (5,6):
                report_type = 'B'
            elif wc_cd == 'WSF60' and barcode.prodlabel_cycles == 2:
                report_type = 'B'
            else:
                report_type = 'G'

            opr_no = '10'

            assn_record = {
                'barcode': barcode.barcode,
                'PRODT_ORDER_NO': order.PRODT_ORDER_NO,
                'OPR_NO': opr_no,
                'REPORT_TYPE': report_type,
                'WC_CD': wc_cd,
                'INSRT_DT': barcode.INSRT_DT,
                'INSRT_USR': barcode.INSRT_USR,
                'UPDT_DT': barcode.UPDT_DT,
                'UPDT_USR': barcode.UPDT_USR
            }
            assn_records.append(assn_record)

            if report_type == 'G':
                order.PROD_QTY_IN_ORDER_UNIT += 1
            else:
                order.BAD_QTY_IN_ORDER_UNIT += 1

            if (order.PROD_QTY_IN_ORDER_UNIT + order.BAD_QTY_IN_ORDER_UNIT) >= order.PRODT_ORDER_QTY:
                order.ORDER_STATUS = 'CL'
                order_indices[wc_cd] += 1
                if order_indices[wc_cd] >= len(orders[wc_cd]):
                    order_indices[wc_cd] = len(orders[wc_cd]) - 1

            barcode.REPORT_FLAG = 'Y'
            updated_barcodes.append(barcode)

    if assn_records:
        db.session.bulk_insert_mappings(Production_Barcode_Assign, assn_records)
    if updated_barcodes:
        db.session.bulk_update_mappings(Production_Barcode, [barcode.__dict__ for barcode in updated_barcodes])

    db.session.commit()

    insert_production_results(orders)


def insert_production_results(orders):
    result_records = []

    for wc_cd in orders.keys():
        for order in orders[wc_cd]:
            if order.ORDER_STATUS == 'CL' or order.PROD_QTY_IN_ORDER_UNIT > 0 or order.BAD_QTY_IN_ORDER_UNIT > 0:
                existing_good_qty = db.session.query(
                    db.func.sum(Production_Results.TOTAL_QTY)
                ).filter(
                    Production_Results.PRODT_ORDER_NO == order.PRODT_ORDER_NO,
                    Production_Results.REPORT_TYPE == 'G'
                ).scalar() or 0

                existing_bad_qty = db.session.query(
                    db.func.sum(Production_Results.TOTAL_QTY)
                ).filter(
                    Production_Results.PRODT_ORDER_NO == order.PRODT_ORDER_NO,
                    Production_Results.REPORT_TYPE == 'B'
                ).scalar() or 0

                good_qty = order.PROD_QTY_IN_ORDER_UNIT - existing_good_qty
                bad_qty = order.BAD_QTY_IN_ORDER_UNIT - existing_bad_qty

                seq = Production_Results.query.filter_by(PRODT_ORDER_NO=order.PRODT_ORDER_NO).count() + 1
                if good_qty > 0:
                    result_record_good = {
                        'PRODT_ORDER_NO': order.PRODT_ORDER_NO,
                        'OPR_NO': '10',
                        'SEQ': seq,
                        'REPORT_TYPE': 'G',
                        'TOTAL_QTY': good_qty,
                        'PLANT_CD': 'P710',
                        'REPORT_DT': None
                    }
                    result_records.append(result_record_good)

                if bad_qty > 0:
                    seq += 1
                    result_record_bad = {
                        'PRODT_ORDER_NO': order.PRODT_ORDER_NO,
                        'OPR_NO': '10',
                        'SEQ': seq,
                        'REPORT_TYPE': 'B',
                        'TOTAL_QTY': bad_qty,
                        'PLANT_CD': 'P710',
                        'REPORT_DT': None
                    }
                    result_records.append(result_record_bad)

                order.PROD_QTY_IN_ORDER_UNIT = existing_good_qty + good_qty
                order.BAD_QTY_IN_ORDER_UNIT = existing_bad_qty + bad_qty

    if result_records:
        db.session.bulk_insert_mappings(Production_Results, result_records)

    db.session.commit()


@bp.route('/assign-orders', methods=['POST'])
def assign_orders_route():
    assign_production_orders()
    return '<script>alert("생산 오더가 할당되었습니다."); window.location.href="/product/assign/";</script>'


