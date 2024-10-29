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
from pybo.models import Production_Order, Item, Work_Center, Plant, Bom, Production_Alpha, Production_Barcode,  \
    Production_Barcode_Assign, Production_Results, kst_now, Packing_Hdr, Packing_Dtl, Item_Master, Biz_Partner, Purchase_Order, Storage_Location, Packing_Cs, Bom_Detail, Storage_Location
from collections import defaultdict

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
    ORDER_STATUS = ''
    RELEASE_START_DT = None  # Release 시작일
    RELEASE_END_DT = None    # Release 종료일
    PRODT_ORDER_NO = ''
    ALPHA_CODE = ''  # ALPHA_CODE 추가
    SL_CD = ''  # 창고코드 추가

    plants = db.session.query(Plant).all()

    if request.method == 'POST':
        form_submitted = True
        PLANT_CD = request.form.get('plant_code', '')
        WC_CD = request.form.get('wc_cd', '')
        ITEM_CD = request.form.get('item_cd', '')
        ORDER_STATUS = request.form.get('order_status', '')
        RELEASE_START_DT = request.form.get('start_date', '')  # 시작일을 Release 날짜로 변경
        RELEASE_END_DT = request.form.get('end_date', '')      # 종료일을 Release 날짜로 변경
        PRODT_ORDER_NO = request.form.get('prodt_order_no', '')
        ALPHA_CODE = request.form.get('alpha_code', '')  # ALPHA_CODE 가져오기
        SL_CD = request.form.get('sl_cd', '')  # SL_CD 가져오기

        if RELEASE_START_DT:
            RELEASE_START_DT = datetime.strptime(RELEASE_START_DT, '%Y-%m-%d')
        if RELEASE_END_DT:
            RELEASE_END_DT = datetime.strptime(RELEASE_END_DT, '%Y-%m-%d')
    else:
        if plants:
            PLANT_CD = plants[0].PLANT_CD

    if not RELEASE_START_DT:
        RELEASE_START_DT = datetime.today()
    if not RELEASE_END_DT:
        RELEASE_END_DT = datetime.today() + timedelta(days=30)

    # 아이템과 관련된 쿼리
    orders_with_items = db.session.query(
        Production_Order, Item, Storage_Location
    ).join(
        Item, Production_Order.ITEM_CD == Item.ITEM_CD
    ).join(
        Item_Master, Item.ALPHA_CODE == Item_Master.ALPHA_CODE
    ).join(
        Storage_Location, Production_Order.SL_CD == Storage_Location.SL_CD
    )

    if PLANT_CD:
        orders_with_items = orders_with_items.filter(Production_Order.PLANT_CD == PLANT_CD)
    if WC_CD:
        orders_with_items = orders_with_items.filter(Production_Order.WC_CD == WC_CD)
    if ITEM_CD:
        orders_with_items = orders_with_items.filter(Production_Order.ITEM_CD == ITEM_CD)
    if ORDER_STATUS:
        orders_with_items = orders_with_items.filter(Production_Order.ORDER_STATUS == ORDER_STATUS)
    if RELEASE_START_DT and RELEASE_END_DT:
        orders_with_items = orders_with_items.filter(Production_Order.RELEASE_DT.between(RELEASE_START_DT, RELEASE_END_DT))
    if PRODT_ORDER_NO:
        orders_with_items = orders_with_items.filter(Production_Order.PRODT_ORDER_NO == PRODT_ORDER_NO)
    if ALPHA_CODE:  # ALPHA_CODE 필터링 추가
        orders_with_items = orders_with_items.filter(Item_Master.ALPHA_CODE == ALPHA_CODE)
    if SL_CD:  # SL_CD 필터링 추가
        orders_with_items = orders_with_items.filter(Production_Order.SL_CD == SL_CD)

    orders_with_items = orders_with_items.all()

    # 작업 센터와 관련된 쿼리
    orders_with_wcs = db.session.query(
        Production_Order, Work_Center, Storage_Location
    ).join(
        Work_Center, Production_Order.WC_CD == Work_Center.WC_CD
    ).join(
        Item, Production_Order.ITEM_CD == Item.ITEM_CD
    ).join(
        Item_Master, Item.ALPHA_CODE == Item_Master.ALPHA_CODE
    ).join(
        Storage_Location, Production_Order.SL_CD == Storage_Location.SL_CD
    )

    if PLANT_CD:
        orders_with_wcs = orders_with_wcs.filter(Production_Order.PLANT_CD == PLANT_CD)
    if WC_CD:
        orders_with_wcs = orders_with_wcs.filter(Production_Order.WC_CD == WC_CD)
    if ITEM_CD:
        orders_with_wcs = orders_with_wcs.filter(Production_Order.ITEM_CD == ITEM_CD)
    if ORDER_STATUS:
        orders_with_wcs = orders_with_wcs.filter(Production_Order.ORDER_STATUS == ORDER_STATUS)
    if RELEASE_START_DT and RELEASE_END_DT:
        orders_with_wcs = orders_with_wcs.filter(Production_Order.RELEASE_DT.between(RELEASE_START_DT, RELEASE_END_DT))
    if PRODT_ORDER_NO:
        orders_with_wcs = orders_with_wcs.filter(Production_Order.PRODT_ORDER_NO == PRODT_ORDER_NO)
    if ALPHA_CODE:  # ALPHA_CODE 필터링 추가
        orders_with_wcs = orders_with_wcs.filter(Item_Master.ALPHA_CODE == ALPHA_CODE)
    if SL_CD:  # SL_CD 필터링 추가
        orders_with_wcs = orders_with_wcs.filter(Production_Order.SL_CD == SL_CD)

    orders_with_wcs = orders_with_wcs.all()

    work_centers = db.session.query(Work_Center).all()
    items = db.session.query(Item).all()
    alpha_codes = db.session.query(Item_Master.ALPHA_CODE).distinct().all()  # ALPHA_CODE 목록 가져오기
    storage_locations = db.session.query(Storage_Location).all()  # 창고 목록 가져오기

    return render_template('product/product_order.html',
                           orders_with_items=orders_with_items,
                           orders_with_wcs=orders_with_wcs,
                           plants=plants,
                           work_centers=work_centers,
                           items=items,
                           alpha_codes=alpha_codes,  # 템플릿에 ALPHA_CODE 목록 전달
                           storage_locations=storage_locations,  # 템플릿에 창고 목록 전달
                           PLANT_CD=PLANT_CD, WC_CD=WC_CD, ITEM_CD=ITEM_CD, ORDER_STATUS=ORDER_STATUS,
                           RELEASE_START_DT=RELEASE_START_DT,  # Release 날짜 반영
                           PRODT_ORDER_NO=PRODT_ORDER_NO, RELEASE_END_DT=RELEASE_END_DT,  # Release 날짜 반영
                           ALPHA_CODE=ALPHA_CODE, SL_CD=SL_CD,  # 템플릿에 선택된 ALPHA_CODE 및 SL_CD 전달
                           form_submitted=form_submitted)


@bp.route('/get_bom_data')
def get_bom_data():
    order_no = request.args.get('order_no')
    item_cd = request.args.get('item_cd')

    # 로그: 입력된 파라미터 확인
    print(f"Received order_no: {order_no}, item_cd: {item_cd}")

    # 단일 단계 조회 쿼리 - 선택된 품목의 바로 하위 자품목만 조회
    bom_data = db.session.query(Bom_Detail, Item).join(
        Item, Bom_Detail.CHILD_ITEM_CD == Item.ITEM_CD
    ).filter(
        Bom_Detail.PRNT_ITEM_CD == item_cd
    ).all()

    # 로그: 쿼리 결과 확인
    print(f"Fetched bom_data: {bom_data}")

    # 조회된 데이터를 리스트로 변환
    results = []
    for bom_detail, item in bom_data:
        result_item = {
            'child_item_cd': bom_detail.CHILD_ITEM_CD,
            'child_item_nm': item.ITEM_NM if item else None,
            'spec': item.SPEC if item else None,
            'child_item_unit': bom_detail.CHILD_ITEM_UNIT,
            'child_item_qty': bom_detail.CHILD_ITEM_QTY
        }
        results.append(result_item)

        # 로그: 개별 항목 확인
        print(f"Processed result item: {result_item}")

    # 최종 결과 확인
    print(f"Final JSON response: {results}")

    return jsonify(results)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/upload_excel', methods=['POST'])
def upload_excel():
    if 'excelFile' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('product.product_register'))
    file = request.files['excelFile']
    if file.filename == '':
        flash('엑셀 파일을 선택해 주세요.', 'error')
        return redirect(url_for('product.product_register'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        duplicate_count = process_excel(filepath)

        if isinstance(duplicate_count, int) and duplicate_count > 0:
            # 중복 데이터에 대한 경고 메시지 표시
            flash(f'{duplicate_count}건의 중복데이터가 인식되었습니다. 중복데이터를 제외한 데이터만 업로드됩니다.', 'error')
        else:
            flash('Excel 파일 업로드 완료.', 'success')

        return redirect(url_for('product.product_register'))
    else:
        flash('Allowed file types are xls, xlsx', 'error')
        return redirect(url_for('product.product_register'))


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
    duplicate_count = 0

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
            'INSRT_USR': g.user.USR_ID,
            'UPDT_DT': convert_value(row.get('UPDT_DT')),
            'UPDT_USR': g.user.USR_ID,
            'REPORT_FLAG': convert_value(row.get('REPORT_FLAG'))
        }

        if existing_record:
            if existing_record.modified != modified:
                for key, value in record_data.items():
                    setattr(existing_record, key, value)
                update_records.append(existing_record)
            else:

                duplicate_count += 1
        else:
            new_records.append(record_data)

    if new_records:
        db.session.bulk_insert_mappings(Production_Alpha, new_records)
    if update_records:
        db.session.bulk_update_mappings(Production_Alpha, [record.__dict__ for record in update_records])

    db.session.commit()

    return duplicate_count  # 중복 데이터 개수를 반환

# 엑셀데이터 조회화면
@bp.route('/product_excel_result/', methods=['GET', 'POST'])
def product_excel_result():
    # 기본 조회 화면으로 이동
    query = db.session.query(Production_Alpha)

    # 조건이 추가될 경우 필터링 처리 가능
    barcode = request.form.get('barcode', '').strip()
    product = request.form.get('product', '').strip()
    lot = request.form.get('lot', '').strip()

    if barcode:
        query = query.filter(Production_Alpha.barcode.like(f'%{barcode}%'))
    if product:
        query = query.filter(Production_Alpha.product.like(f'%{product}%'))
    if lot:
        query = query.filter(Production_Alpha.LOT.like(f'%{lot}%'))

    # 쿼리 실행
    alpha_data = query.all()
    return render_template('product/product_excel_result.html', alpha_data=alpha_data, barcode=barcode, product=product, lot=lot)






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
            INSRT_DT_END = datetime.strptime(INSRT_DT_END, '%Y-%m-%d') + timedelta(days=1, seconds=-1)

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

    all_results = query.all()

    # 중복된 바코드 데이터를 그룹화하여 하나의 바코드당 제조오더번호 목록을 생성
    grouped_results = defaultdict(list)
    for idx, result in enumerate(all_results):
        grouped_results[result[0].barcode].append((idx + 1, result))

    return render_template('product/product_register_result.html',
                           grouped_results=grouped_results,
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

    # Work_Center에서 공정과 PASS_CONDITION 정보 -> 이 정보로 양불 판단 진행 -> 기준정보 활용.
    work_centers = db.session.query(Work_Center.WC_CD, Work_Center.PASS_CONDITION).all()

    new_alpha_records = []
    new_barcode_records = []
    updated_alpha_records = []

    for record_id in selected_records:
        barcode, modified_str = record_id.split('|')
        modified = parse_datetime(modified_str)
        alpha_record = Production_Alpha.query.filter_by(barcode=barcode).first()

        if alpha_record:
            # 바코드 실적에 추가할 항목
            barcode_record = {
                'LOT': alpha_record.LOT,
                'product': alpha_record.product,
                'barcode': alpha_record.barcode,
                'modified': alpha_record.modified,
                'err_code': alpha_record.err_code,
                'err_info': alpha_record.err_info,
                'print_time': alpha_record.print_time,
                'inweight_time': alpha_record.inweight_time,
                'inweight_cycles': alpha_record.inweight_cycles,
                'inweight_station': alpha_record.inweight_station,
                'inweight_result': alpha_record.inweight_result,
                'inweight_value': alpha_record.inweight_value,
                'leaktest_cycles': alpha_record.leaktest_cycles,
                'leaktest_entry': alpha_record.leaktest_entry,
                'leaktest_exit': alpha_record.leaktest_exit,
                'leaktest_station': alpha_record.leaktest_station,
                'leaktest_value': alpha_record.leaktest_value,
                'leaktest_ptest': alpha_record.leaktest_ptest,
                'leaktest_duration': alpha_record.leaktest_duration,
                'leaktest_result': alpha_record.leaktest_result,
                'outweight_time': alpha_record.outweight_time,
                'outweight_station': alpha_record.outweight_station,
                'outweight_cycles': alpha_record.outweight_cycles,
                'outweight_result': alpha_record.outweight_result,
                'outweight_value': alpha_record.outweight_value,
                'itest2_time': alpha_record.itest2_time,
                'itest2_station': alpha_record.itest2_station,
                'itest2_cycles': alpha_record.itest2_cycles,
                'itest2_result': alpha_record.itest2_result,
                'itest2_value': alpha_record.itest2_value,
                'itest2_ptest': alpha_record.itest2_ptest,
                'prodlabel_time': alpha_record.prodlabel_time,
                'prodlabel_cycles': alpha_record.prodlabel_cycles,
                'INSRT_DT': alpha_record.INSRT_DT,
                'INSRT_USR': g.user.USR_ID,
                'UPDT_DT': alpha_record.UPDT_DT,
                'UPDT_USR': g.user.USR_ID,
                'REPORT_FLAG': alpha_record.REPORT_FLAG
            }
            new_barcode_records.append(barcode_record)

            processes = []

            # 각 공정에 따라 PASS_CONDITION 기반 양불 판단 -> 작업장 테이블에 양불 포인트를 적어서 동적으로 처리되도록 변경 -> 기준정보 활용.
            for wc_cd, pass_condition in work_centers:

                if pass_condition:
                    result_value = getattr(alpha_record, pass_condition, None)  # 조건 필드를 동적으로 참조
                    if result_value == 1:
                        processes.append((wc_cd, 'G'))
                    else:
                        processes.append((wc_cd, 'B'))
                else:
                    # pass_condition이 None일 경우 기본 불량으로 설정하거나 생략
                    processes.append((wc_cd, 'B'))

            # 각 공정에 대한 실적 생성
            for wc_cd, report_type in processes:
                assn_record = {
                    'barcode': alpha_record.barcode,
                    'PRODT_ORDER_NO': None,
                    'OPR_NO': '10',
                    'REPORT_TYPE': report_type,
                    'WC_CD': wc_cd,
                    'INSRT_USR': g.user.USR_ID,
                    'UPDT_USR': g.user.USR_ID
                }
                new_alpha_records.append(assn_record)

            alpha_record.REPORT_FLAG = 'Y'
            updated_alpha_records.append(alpha_record)

    if new_barcode_records:
        db.session.bulk_insert_mappings(Production_Barcode, new_barcode_records)
    if new_alpha_records:
        db.session.bulk_insert_mappings(Production_Barcode_Assign, new_alpha_records)
    if updated_alpha_records:
        db.session.bulk_update_mappings(Production_Alpha, [record.__dict__ for record in updated_alpha_records])

    db.session.commit()
    assign_production_orders()

    flash('실적처리 완료.', 'success')
    return redirect(url_for('product.product_register'))


def assign_production_orders():
    # Work_Center에서 모든 공정을 동적으로 가져옴 -> 기준정보 활용.
    work_centers = db.session.query(Work_Center.WC_CD).all()

    # PRODT_ORDER_NO가 없는 바코드 실적을 Production_Barcode와 조인하여 가져오기
    barcodes = db.session.query(Production_Barcode_Assign, Production_Barcode.product).join(
        Production_Barcode, Production_Barcode_Assign.barcode == Production_Barcode.barcode
    ).filter(
        Production_Barcode_Assign.PRODT_ORDER_NO == None
    ).all()

    # 공정 별 오더 검색
    orders = {wc_cd: {} for wc_cd, in work_centers}
    for wc_cd, in work_centers:
        wc_orders = db.session.query(Production_Order, Item).join(
            Item, Production_Order.ITEM_CD == Item.ITEM_CD
        ).filter(
            Production_Order.WC_CD == wc_cd
        ).all()

        for order, item in wc_orders:
            alpha_code = item.ALPHA_CODE
            if alpha_code not in orders[wc_cd]:
                orders[wc_cd][alpha_code] = []
            orders[wc_cd][alpha_code].append(order)

    # 각 공정의 오더 인덱스를 관리하여 오더 할당
    order_indices = {wc_cd: {} for wc_cd in orders.keys()}
    assn_records = []

    for barcode_assign, barcode_product in barcodes:
        wc_cd = barcode_assign.WC_CD
        if wc_cd in orders and barcode_product in orders[wc_cd]:
            order_list = orders[wc_cd][barcode_product]

            if barcode_product not in order_indices[wc_cd]:
                order_indices[wc_cd][barcode_product] = 0

            order = order_list[order_indices[wc_cd][barcode_product]]

            # Order 객체인지 확인 후 처리
            if isinstance(order, Production_Order):
                barcode_assign.PRODT_ORDER_NO = order.PRODT_ORDER_NO
                if barcode_assign.REPORT_TYPE == 'G':
                    order.PROD_QTY_IN_ORDER_UNIT += 1
                else:
                    order.BAD_QTY_IN_ORDER_UNIT += 1

                # 오더 수량 초과 시 다음 오더로 이동
                if (order.PROD_QTY_IN_ORDER_UNIT + order.BAD_QTY_IN_ORDER_UNIT) >= order.PRODT_ORDER_QTY:
                    order.ORDER_STATUS = 'CL'
                    order_indices[wc_cd][barcode_product] += 1
                    if order_indices[wc_cd][barcode_product] >= len(order_list):
                        order_indices[wc_cd][barcode_product] = len(order_list) - 1

                barcode_assign.INSRT_USR = g.user.USR_ID
                barcode_assign.UPDT_USR = g.user.USR_ID
                assn_records.append(barcode_assign)

        else:
            print(f"No matching order found for barcode: {barcode_assign.barcode} with product: {barcode_product}")
            continue

    if assn_records:
        db.session.bulk_update_mappings(Production_Barcode_Assign, [record.__dict__ for record in assn_records])

    db.session.commit()
    insert_production_results(orders)


def insert_production_results(orders):
    result_records = []

    for wc_cd in orders.keys():
        for alpha_code in orders[wc_cd].keys():
            for order in orders[wc_cd][alpha_code]:
                if isinstance(order, Production_Order):
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
                            result_records.append({
                                'PRODT_ORDER_NO': order.PRODT_ORDER_NO,
                                'OPR_NO': '10',
                                'WC_CD': order.WC_CD,
                                'SEQ': seq,
                                'REPORT_TYPE': 'G',
                                'TOTAL_QTY': good_qty,
                                'PLANT_CD': 'P710',
                                'INSRT_USR': g.user.USR_ID,
                                'UPDT_USR': g.user.USR_ID
                            })

                        if bad_qty > 0:
                            seq += 1
                            result_records.append({
                                'PRODT_ORDER_NO': order.PRODT_ORDER_NO,
                                'OPR_NO': '10',
                                'WC_CD': order.WC_CD,
                                'SEQ': seq,
                                'REPORT_TYPE': 'B',
                                'TOTAL_QTY': bad_qty,
                                'PLANT_CD': 'P710',
                                'INSRT_USR': g.user.USR_ID,
                                'UPDT_USR': g.user.USR_ID
                            })

                        order.PROD_QTY_IN_ORDER_UNIT = existing_good_qty + good_qty
                        order.BAD_QTY_IN_ORDER_UNIT = existing_bad_qty + bad_qty

    if result_records:
        db.session.bulk_insert_mappings(Production_Results, result_records)

    db.session.commit()

@bp.route('/assign-orders', methods=['POST'])
def assign_orders_route():
    assign_production_orders()
    return '<script>alert("생산 오더가 할당되었습니다."); window.location.href="/product/assign/";</script>'

#60이 완료되면 70제조 오더는 mes에서만 따로 진행해야함 -> 60까지 양품이 계획수량까지 완성되면 제조오더를 자동생성해서 packing로직으로 넘어가게 하는 과정 구현 요구됨
@bp.route('/register_result_packing/', methods=['GET', 'POST'])
def product_register_packing():
    form_submitted = False
    PLANT_CD = ''
    WC_CD = 'WSF70'  # 작업공정 고정 값
    ITEM_CD = ''  # 품목 고정 값
    ORDER_STATUS = ''
    PLANT_START_DT = datetime.today()
    PLANT_COMPT_DT = datetime.today() + timedelta(days=30)
    PRODT_ORDER_NO = ''

    plants = db.session.query(Production_Order.PLANT_CD).distinct().all()
    items = db.session.query(Item.ITEM_CD).distinct().all()

    if request.method == 'POST':
        form_submitted = True
        PLANT_CD = request.form.get('plant_code', '')
        ORDER_STATUS = request.form.get('order_status', '')
        PLANT_START_DT = request.form.get('start_date', '')
        PLANT_COMPT_DT = request.form.get('end_date', '')
        PRODT_ORDER_NO = request.form.get('prodt_order_no', '')

        if PLANT_START_DT:
            PLANT_START_DT = datetime.strptime(PLANT_START_DT, '%Y-%m-%d')
        else:
            PLANT_START_DT = datetime.today()

        if PLANT_COMPT_DT:
            PLANT_COMPT_DT = datetime.strptime(PLANT_COMPT_DT, '%Y-%m-%d')
        else:
            PLANT_COMPT_DT = datetime.today() + timedelta(days=30)
    else:
        if plants:
            PLANT_CD = plants[0][0]  # 첫 번째 공장을 기본값으로 설정

    # Packing_Hdr와 Production_Order, Item을 조인하여 주문 정보 조회
    query = db.session.query(Packing_Hdr).join(
        Production_Order, Packing_Hdr.prodt_order_no == Production_Order.PRODT_ORDER_NO
    ).join(
        Item, Production_Order.ITEM_CD == Item.ITEM_CD
    )

    # 필터링 조건 추가
    if PLANT_CD:
        query = query.filter(Production_Order.PLANT_CD == PLANT_CD)
    if WC_CD:
        query = query.filter(Production_Order.WC_CD == WC_CD)
    if ITEM_CD:
        query = query.filter(Production_Order.ITEM_CD == ITEM_CD)
    if ORDER_STATUS:
        query = query.filter(Production_Order.ORDER_STATUS == ORDER_STATUS)
    if PLANT_START_DT:
        query = query.filter(Production_Order.PLANT_START_DT >= PLANT_START_DT)
    if PLANT_COMPT_DT:
        query = query.filter(Production_Order.PLANT_COMPT_DT <= PLANT_COMPT_DT)
    if PRODT_ORDER_NO:
        query = query.filter(Production_Order.PRODT_ORDER_NO == PRODT_ORDER_NO)

    orders_with_hdr = query.all()

    # Packing_Cs 모델에서 제조오더번호별로 MasterBoxNo를 조회
    packing_cs_data = db.session.query(Packing_Cs.prodt_order_no, Packing_Cs.m_box_no).all()

    # 제조오더번호별로 MasterBoxNo를 그룹화
    master_box_grouped = defaultdict(list)
    for order_no, m_box_no in packing_cs_data:
        master_box_grouped[order_no].append(m_box_no)

    work_centers = db.session.query(Work_Center).all()
    items = db.session.query(Item).all()

    return render_template('product/product_register_packing.html',
                           orders_with_hdr=orders_with_hdr,
                           plants=plants,
                           work_centers=work_centers,
                           items=items,
                           master_box_grouped=master_box_grouped,  # MasterBoxNo 데이터를 템플릿에 전달
                           PLANT_CD=PLANT_CD, WC_CD=WC_CD, ITEM_CD=ITEM_CD, ORDER_STATUS=ORDER_STATUS,
                           PLANT_START_DT=PLANT_START_DT,
                           PRODT_ORDER_NO=PRODT_ORDER_NO, PLANT_COMPT_DT=PLANT_COMPT_DT,
                           form_submitted=form_submitted)


# 바코드 스캔 데이터 검증 로직
@bp.route('/check_barcode/', methods=['POST'])
def check_barcode():
    barcode = request.json.get('barcode')
    if not barcode:
        return jsonify({"status": "error", "message": "Barcode is required"}), 400

    # 기존 Production_Barcode_Assign 검증 로직 유지
    barcode_data = db.session.query(Production_Barcode_Assign).filter(
        Production_Barcode_Assign.barcode == barcode,
        Production_Barcode_Assign.WC_CD == 'WSF60',
        Production_Barcode_Assign.REPORT_TYPE == 'G'
    ).first()
    print(f"Received barcode: {barcode}")

    if barcode_data:
        # 바코드가 유효한 경우, Product_Alpha에서 LOT 값을 조회
        product_alpha = db.session.query(Production_Alpha).filter_by(barcode=barcode).first()

        if product_alpha:
            lot_no = product_alpha.LOT  # LOT 값을 가져옴
            return jsonify({"status": "success", "message": "PASS", "lot": lot_no})
        else:
            return jsonify({"status": "success", "message": "PASS", "lot": None})
    else:
        return jsonify({"status": "fail", "message": "FAIL"})




# box 번호 자동으로 넘어가는 로직
@bp.route('/get_next_master_box_no/', methods=['GET'])
def get_next_master_box_no():
    last_master_box_no = db.session.query(func.max(Packing_Cs.m_box_no)).filter(
        Packing_Cs.m_box_no.like('0880%')).scalar()
    if last_master_box_no:
        next_master_box_no = int(last_master_box_no[4:]) + 1
        next_master_box_no = '0880' + str(next_master_box_no).zfill(8)
    else:
        next_master_box_no = '088000000001'

    return jsonify({"status": "success", "next_master_box_no": next_master_box_no})


def date_to_hex(date_obj):
    year = date_obj.year % 100  # 마지막 두 자리만 사용
    month = date_obj.month
    day = date_obj.day
    return f"{year:02X}{month:02X}{day:02X}"  # 16진수로 변환

def generate_new_serial(date_obj):
    # 날짜를 16진수로 변환 (예: '7E912')
    date_hex = date_to_hex(date_obj)

    # 오늘 날짜에 해당하는 시리얼 번호 중 가장 큰 값 조회 (예: 7E9120001 형태)
    max_serial = db.session.query(func.max(Packing_Cs.cs_udi_serial)).filter(
        Packing_Cs.cs_udi_serial.like(f"{date_hex}%")
    ).scalar()

    if max_serial:
        # 16진수 날짜 뒤의 숫자 부분 추출, 숫자로 변환 후 1 증가
        last_sequence = int(max_serial[-3:])  # 마지막 3자리 숫자
        new_sequence = last_sequence + 1
    else:
        # 처음 생성되는 시리얼 번호
        new_sequence = 1

    # 새로운 시리얼 번호 생성 (예: '7E912001')
    new_serial = f"{date_hex}{new_sequence:03}"
    return new_serial

# 데이터 db에 insert
@bp.route('/save_packing_data/', methods=['POST'])
def save_packing_data():
    try:
        # 클라이언트에서 전송된 JSON 데이터 수신
        data = request.json
        logging.info(f"Received packing data: {data}")

        # 데이터 할당
        prodt_order_no = data['prodt_order_no']
        master_box_no = data['master_box_no']
        lot_no = data['lot_no']
        quantity = data['quantity']
        prod_qty = int(data['quantity'])
        packing_dt = datetime.now()  # 현재 시간을 사용하여 패킹일자 설정
        expiry_date = datetime.strptime(data['expiry_date'], '%Y-%m-%d')
        rows = data['rows']  # UDI QR 및 Barcode 데이터가 포함된 리스트
        cs_udi_serial = generate_new_serial(packing_dt)

        # Production_Order 모델에서 prodt_order_no로 ITEM_CD 조회
        production_order = db.session.query(Production_Order).filter_by(PRODT_ORDER_NO=prodt_order_no).first()
        if not production_order:
            raise Exception(f"Production order {prodt_order_no} not found")

        item_cd = production_order.ITEM_CD  # 조회된 ITEM_CD

        # Item 모델에서 해당 ITEM_CD로 alpha_code 조회
        item = db.session.query(Item).filter_by(ITEM_CD=item_cd).first()
        if not item:
            raise Exception(f"Item with ITEM_CD {item_cd} not found")

        alpha_code = item.ALPHA_CODE  # 조회된 alpha_code

        # Item 모델에서 alpha_code로 ITEM_ACC가 '10'인 데이터의 ITEM_CD 조회
        cs_model_item = db.session.query(Item).filter_by(ALPHA_CODE=alpha_code, ITEM_ACCT='10').first()
        if not cs_model_item:
            raise Exception(f"Item with ALPHA_CODE {alpha_code} and ITEM_ACCT '10' not found")

        cs_model = cs_model_item.ITEM_NM  # 최종적으로 조회된 ITEM_NM가 cs_model

        logging.info(f"Processing order: {prodt_order_no} with master box no: {master_box_no} and cs_model: {cs_model}")

        # P_PACKING_DTL 테이블에 각 행 데이터를 삽입
        for row in rows:
            # barcode의 마지막 1자리 제거
            modified_barcode = row['udi_qr'][:-1]  # 마지막 한 자리를 제거

            dtl = Packing_Dtl(
                m_box_no=master_box_no,
                lot_no=lot_no,
                barcode=modified_barcode,  # 수정된 바코드
                udi_code=row['barcode'],  # 각 행의 바코드
                packing_dt=packing_dt,  # 패킹일자
                exp_date=expiry_date  # 만기일자
            )
            db.session.add(dtl)  # 데이터베이스에 삽입 대기
            logging.info(f"Added Packing Detail: {dtl}")

            # P_PRODUCTION_BARCODE_ASSN 테이블에 barcode로 데이터 삽입
            barcode_assn = Production_Barcode_Assign(
                barcode=modified_barcode,  # 수정된 바코드 사용
                PRODT_ORDER_NO=prodt_order_no,
                BOX_NUM=master_box_no,
                OPR_NO='10',  # 고정 값
                WC_CD='WSF70',  # 고정 값
                REPORT_TYPE='G',  # 고정 값
                INSRT_USR=g.user.USR_ID,  # 유저 정보가 있다면 사용
                UPDT_USR=g.user.USR_ID
            )
            db.session.add(barcode_assn)  # 데이터베이스에 삽입 대기
            logging.info(f"Added Barcode Assignment: {barcode_assn}")

        # P_PACKING_CS 테이블에 마스터 박스 정보 저장
        packing_cs = Packing_Cs(
            prodt_order_no=prodt_order_no,
            cs_model=cs_model,  # 조회된 cs_model 사용
            m_box_no=master_box_no,
            cs_qty=quantity,  # 수량 저장
            cs_lot_no=lot_no,
            cs_udi_di='08809931850003',  # 실제 SynoFlux120L 1개 짜리 DI
            cs_udi_lotno=lot_no,
            cs_udi_prod=packing_dt.strftime('%Y%m%d'),
            cs_prod_date=packing_dt.strftime('%Y%m%d'),  # 패킹일자
            cs_exp_date=expiry_date.strftime('%Y%m%d'),  # 만기일자
            cs_udi_serial=cs_udi_serial,
            cs_udi_qr=f"010880993185000310{lot_no}11{packing_dt.strftime('%Y%m%d')}17{expiry_date.strftime('%Y%m%d')}",
            print_flag="N"  # 기본 프린트 상태
        )

        db.session.add(packing_cs)  # 데이터베이스에 삽입 대기
        logging.info(f"Added Packing Master: {packing_cs}")

        production_order.PROD_QTY_IN_ORDER_UNIT = production_order.PROD_QTY_IN_ORDER_UNIT + prod_qty
        logging.info(f"Updated Production Order: {prodt_order_no}, new PROD_QTY_IN_ORDER_UNIT: {production_order.PROD_QTY_IN_ORDER_UNIT}")

        # 트랜잭션 커밋 (모든 작업 완료 후 DB에 반영)
        db.session.commit()
        logging.info("Transaction committed successfully")
        return jsonify({"status": "success"})  # 성공 응답 전송

    except Exception as e:
        db.session.rollback()  # 오류 발생 시 트랜잭션 롤백
        logging.error(f"Error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------------

@bp.route('/print_label/', methods=['POST'])
def print_label():
    try:
        # 클라이언트에서 박스 번호를 받음
        box_no = request.json.get('box_no')
        if not box_no:
            return jsonify({'error': '박스 번호가 제공되지 않았습니다.'}), 400

        # 박스 번호에 해당하는 레코드를 찾음
        print_data = db.session.query(Print_Cs).filter_by(m_box_no=box_no).first()
        if not print_data:
            return jsonify({'error': '해당 박스 번호에 대한 데이터를 찾을 수 없습니다.'}), 404

        logging.info("Creating CODESOFT application object...")
        codesoft = win32com.client.Dispatch("Lppx2.Application")
        if codesoft is None:
            raise Exception("Failed to create CodeSoft COM object.")
        logging.info("CODESOFT application object created successfully.")

        # Set the application to be visible
        codesoft.Visible = True

        # 라벨 파일 경로 설정
        label_path = r'C:\\Users\\user\\Desktop\\디지털정보화팀\\flask-master\\pybo\\static\\lbl\\boxno.lab'
        logging.info(f"Label document path: {label_path}")

        # 파일 존재 여부 확인
        if not os.path.exists(label_path):
            error_msg = f"Label file does not exist at {label_path}"
            logging.error(error_msg)
            return jsonify({'error': error_msg}), 500

        # 라벨 파일 열기
        logging.info("Opening label document...")
        label_document = codesoft.Documents.Open(label_path, True)
        if label_document is None:
            raise Exception("Failed to open the label document.")
        logging.info("Label document opened successfully.")

        # 라벨 프린터 설정 및 출력
        logging.info("Printing document...")
        label_document.PrintDocument(1)  # 1 장 인쇄
        logging.info("Document printed successfully.")

        # print_flag를 'Y'로 업데이트
        print_data.print_flag = 'Y'
        db.session.commit()  # 변경 사항 저장

        label_document.Close(False)
        logging.info("Label document closed.")

        return jsonify({'message': 'Label document opened and printed successfully.'})
    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        return jsonify({'error': str(e)}), 500



# --------------------------------------------------------
# 재프린트 로직 Y를 다시 N으로 바꿔서 프린트로직 똑같이 태우고 프린트 완료되면 다시 Y로 바꾸는 방식
@bp.route('/reprint_label/<box_no>', methods=['POST'])
def reprint_label(box_no):
    try:
        # Step 1: Print_Cs 테이블에서 해당 박스 번호로 print_flag 확인
        print_data = db.session.query(Print_Cs).filter_by(m_box_no=box_no).first()

        if not print_data:
            return jsonify({'error': '해당 박스를 찾을 수 없습니다.'}), 404

        # Step 2: print_flag가 Y일 경우 N으로 설정하여 재프린트를 허용
        if print_data.print_flag == 'Y':
            print_data.print_flag = 'N'
            db.session.commit()

        # Step 3: CodeSoft로 라벨 파일 열고 프린트
        codesoft = win32com.client.Dispatch("Lppx2.Application")
        codesoft.Visible = True

        # 라벨 파일 경로
        label_path = r'C:\\Users\\user\\Desktop\\디지털정보화팀\\flask-master\\pybo\\static\\lbl\\boxno.lab'
        if not os.path.exists(label_path):
            return jsonify({'error': '라벨 파일을 찾을 수 없습니다.'}), 500

        # 라벨 파일을 열고 1장을 출력
        label_document = codesoft.Documents.Open(label_path, True)
        label_document.PrintDocument(1)

        # 라벨 파일 닫기
        label_document.Close(False)

        # Step 4: 프린트 완료 후 print_flag를 다시 Y로 변경
        print_data.print_flag = 'Y'
        db.session.commit()

        return jsonify({'message': '라벨이 성공적으로 재프린트되었습니다.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500




# 외주발주조회
@bp.route('/register_result_sterilizating/', methods=['GET', 'POST'])
def product_register_sterilizating():
    form_submitted = False
    PLANT_CD = ''
    BP_CD = ''  # 외주업체
    ITEM_CD = ''  # 품목 코드
    INSRT_DT_START = None
    INSRT_DT_END = None
    BARCODE_NO_START = ''
    BARCODE_NO_END = ''
    PO_STATUS = 'all'  # 발주 상태

    # 공장 목록, 품목 목록, 외주업체 목록 조회
    plants = db.session.query(Purchase_Order.PLANT_CD).distinct().all()
    items = db.session.query(Item.ITEM_CD, Item.ITEM_NM).distinct().all()
    vendors = db.session.query(Biz_Partner.bp_cd, Biz_Partner.bp_nm).distinct().all()

    if request.method == 'POST':
        form_submitted = True
        PLANT_CD = request.form.get('plant_code', '')
        BP_CD = request.form.get('bp_cd', '')
        ITEM_CD = request.form.get('item_cd', '')
        INSRT_DT_START = request.form.get('start_date', '')
        INSRT_DT_END = request.form.get('end_date', '')
        BARCODE_NO_START = request.form.get('barcode_no_start', '')
        BARCODE_NO_END = request.form.get('barcode_no_end', '')
        PO_STATUS = request.form.get('po_status', 'all')

        # 날짜 값이 있는지 확인하고 변환
        if INSRT_DT_START:
            INSRT_DT_START = datetime.strptime(INSRT_DT_START, '%Y-%m-%d')
        if INSRT_DT_END:
            INSRT_DT_END = datetime.strptime(INSRT_DT_END, '%Y-%m-%d')

    # 기본 날짜 설정
    if not INSRT_DT_START:
        INSRT_DT_START = datetime.today()
    if not INSRT_DT_END:
        INSRT_DT_END = datetime.today() + timedelta(days=30)

    # 쿼리 작성
    query = db.session.query(
        Purchase_Order.PO_NO,
        Purchase_Order.PO_SEQ_NO,
        Purchase_Order.ITEM_CD,
        Purchase_Order.PO_QTY,
        Purchase_Order.OUT_QTY,
        Purchase_Order.IN_QTY,
        Purchase_Order.PO_UNIT,
        Purchase_Order.PO_PRC,
        Purchase_Order.PO_CUR,
        Purchase_Order.DLVY_DT,
        Purchase_Order.STATUS,
        Biz_Partner.bp_cd,
        Biz_Partner.bp_nm,
        Item.ITEM_NM,
        Item.SPEC,
        Item.BASIC_UNIT,
        Storage_Location.SL_NM,
        Storage_Location.SL_CD
    ).join(
        Biz_Partner, Purchase_Order.BP_CD == Biz_Partner.bp_cd
    ).join(
        Item, Purchase_Order.ITEM_CD == Item.ITEM_CD
    ).join(
        Storage_Location, Purchase_Order.SL_CD == Storage_Location.SL_CD
    )

    # 필터링 조건 적용
    if PLANT_CD:
        query = query.filter(Purchase_Order.PLANT_CD == PLANT_CD)
    if BP_CD:
        query = query.filter(Purchase_Order.BP_CD == BP_CD)
    if ITEM_CD:
        query = query.filter(Purchase_Order.ITEM_CD == ITEM_CD)
    if INSRT_DT_START:
        query = query.filter(Purchase_Order.IF_INSRT_DT >= INSRT_DT_START)
    if INSRT_DT_END:
        query = query.filter(Purchase_Order.IF_INSRT_DT <= INSRT_DT_END)

    # PO_STATUS에 따른 필터링
    if PO_STATUS == 'none':  # '미등록' 상태일 경우, None 상태만 필터링
        query = query.filter(Purchase_Order.STATUS.is_(None))
    elif PO_STATUS in ['D', 'R']:  # 선택된 특정 상태만 필터링
        query = query.filter(Purchase_Order.STATUS == PO_STATUS)
    # '전체' 상태는 필터링을 적용하지 않음

    if BARCODE_NO_START and BARCODE_NO_END:
        query = query.filter(Purchase_Order.PO_NO.between(BARCODE_NO_START, BARCODE_NO_END))

    # 결과 조회
    orders_with_hdr = query.all()

    return render_template('product/product_register_sterilizating.html',
                           orders_with_hdr=orders_with_hdr,
                           plants=plants,
                           vendors=vendors,
                           items=items,
                           form_submitted=form_submitted,
                           PLANT_CD=PLANT_CD,
                           BP_CD=BP_CD,
                           ITEM_CD=ITEM_CD,
                           INSRT_DT_START=INSRT_DT_START,
                           INSRT_DT_END=INSRT_DT_END,
                           PO_STATUS=PO_STATUS)


@bp.route('/get_box_details/<box_no>', methods=['GET'])
def get_box_details(box_no):
    # 박스 번호로 해당 데이터를 DB에서 가져옴 (Packing_Dtl)
    box_data = db.session.query(Packing_Dtl).filter_by(m_box_no=box_no).all()

    # Packing_Cs에서 추가 데이터를 조회
    cs_data = db.session.query(Packing_Cs).filter_by(m_box_no=box_no).first()

    rows = []
    for item in box_data:
        rows.append({
            'lot_no': item.lot_no,
            'udi_code': item.udi_code,
            'barcode': item.barcode
        })

    # 추가로 cs_data의 정보를 같이 반환
    cs_details = {
        'cs_model': cs_data.cs_model,
        'cs_prod_date': cs_data.cs_prod_date,
        'cs_exp_date': cs_data.cs_exp_date,
        'cs_udi_serial': cs_data.cs_udi_serial,
        'cs_udi_qr': cs_data.cs_udi_qr
    } if cs_data else {}

    return jsonify({'rows': rows, 'cs_details': cs_details})


# 외주실적등록
@bp.route('/register_result_sterilizating_result/', methods=['GET', 'POST'])
def product_register_sterilizating_result():
    return render_template('product/product_register_sterilizating_result.html')