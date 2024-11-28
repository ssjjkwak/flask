import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import re
import win32com.client
from flask import Blueprint, url_for, render_template, request, current_app, jsonify, g, flash, session
from sqlalchemy import null, func, or_, cast, Date
from werkzeug.utils import redirect, secure_filename
import pandas as pd
from pybo import db
from pybo.models import Production_Order, Item, Work_Center, Plant, Production_Alpha, Production_Barcode,  \
    Barcode_Flow, Production_Results, kst_now, Packing_Hdr, Packing_Dtl, Item_Alpha, Biz_Partner, Purchase_Order, \
    Storage_Location, Packing_Cs, Bom_Detail, Storage_Location, Barcode_Status, Material_Doc, Status
from collections import defaultdict
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy.sql import func


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
        Item_Alpha, Item.ALPHA_CODE == Item_Alpha.ALPHA_CODE
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
        orders_with_items = orders_with_items.filter(Item_Alpha.ALPHA_CODE == ALPHA_CODE)
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
        Item_Alpha, Item.ALPHA_CODE == Item_Alpha.ALPHA_CODE
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
        orders_with_wcs = orders_with_wcs.filter(Item_Alpha.ALPHA_CODE == ALPHA_CODE)
    if SL_CD:  # SL_CD 필터링 추가
        orders_with_wcs = orders_with_wcs.filter(Production_Order.SL_CD == SL_CD)

    orders_with_wcs = orders_with_wcs.all()

    work_centers = db.session.query(Work_Center).all()
    items = db.session.query(Item).all()
    alpha_codes = db.session.query(Item_Alpha.ALPHA_CODE).distinct().all()  # ALPHA_CODE 목록 가져오기
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

# ALPHA 테이블에 엑셀 데이터 INSERT
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

        # 'REPORT_FLAG' 값이 없는 경우 기본값 'N' 설정
        report_flag_value = convert_value(row.get('REPORT_FLAG'))
        report_flag_value = report_flag_value if report_flag_value is not None else 'N'

        insrt_dt_value = convert_value(row.get('INSRT_DT')) or datetime.now()
        updt_dt_value = convert_value(row.get('UPDT_DT')) or datetime.now()

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
            'INSRT_DT': insrt_dt_value,
            'INSRT_USR': g.user.USR_ID,
            'UPDT_DT': updt_dt_value,
            'UPDT_USR': g.user.USR_ID,
            'REPORT_FLAG': report_flag_value
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

    # barcode, product, lot 데이터를 쿼리하여 리스트로 가져옵니다.
    barcodes = db.session.query(Production_Alpha.barcode).distinct().all()
    products = db.session.query(Production_Alpha.product).distinct().all()
    lots = db.session.query(Production_Alpha.LOT).distinct().all()

    # 선택된 필터 조건 가져오기
    barcode = request.form.get('barcode', '').strip()
    product = request.form.get('product', '').strip()
    lot = request.form.get('lot', '').strip()

    # 필터 적용
    if barcode:
        query = query.filter(Production_Alpha.barcode.like(f'%{barcode}%'))
    if product:
        query = query.filter(Production_Alpha.product.like(f'%{product}%'))
    if lot:
        query = query.filter(Production_Alpha.LOT.like(f'%{lot}%'))

    # 쿼리 실행
    alpha_data = query.all()

    # 쿼리 결과와 선택 목록 전달
    return render_template('product/product_excel_result.html',
                           alpha_data=alpha_data,
                           barcodes=barcodes,
                           products=products,
                           lots=lots,
                           barcode=barcode,
                           product=product,
                           lot=lot)

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
        Barcode_Flow,
        Production_Alpha.LOT,
        Production_Alpha.product,
        Barcode_Flow.FROM_SL_CD,  # FROM 창고
        Barcode_Flow.TO_SL_CD,  # TO 창고
        Barcode_Flow.INSRT_DT,  # INSRT 날짜
        Barcode_Flow.UPDT_DT,  # UPDT 날짜
        Barcode_Flow.BOX_NUM,  # Box 번호
        Barcode_Flow.DOC_NO  # 전표번호
    ).join(
        Production_Alpha, Barcode_Flow.barcode == Production_Alpha.barcode
    )

    if LOT_NO_START and LOT_NO_END:
        query = query.filter(Production_Alpha.LOT.between(LOT_NO_START, LOT_NO_END))
    if INSRT_DT_START:
        query = query.filter(Barcode_Flow.INSRT_DT >= INSRT_DT_START)
    if INSRT_DT_END:
        query = query.filter(Barcode_Flow.INSRT_DT <= INSRT_DT_END)
    if BARCODE_NO_START and BARCODE_NO_END:
        query = query.filter(Barcode_Flow.barcode.between(BARCODE_NO_START, BARCODE_NO_END))

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

# BARCODE, BARCODE_FLOW 테이블에 엑셀 데이터 INSERT
@bp.route('/register', methods=['POST'])
def register():
    selected_records = request.form.getlist('chkRow')
    if not selected_records:
        return '<script>alert("실적 처리할 레코드를 선택해 주세요."); window.location.href="/product/register/";</script>'

    logging.info(f"Selected records: {selected_records}")

    try:
        # 미리 필요한 데이터를 한 번에 로드하여 메모리에서 작업
        work_centers = {wc.WC_CD: wc.PASS_CONDITION for wc in db.session.query(Work_Center).all()}
        logging.info(f"Retrieved work centers: {work_centers}")

        # 필요한 데이터를 캐싱하기 위해 바코드 데이터를 미리 가져옴
        barcodes_data = db.session.query(Production_Alpha).filter(
            Production_Alpha.barcode.in_([record_id.split('|')[0] for record_id in selected_records])
        ).all()

        # 필요한 데이터 저장용
        new_alpha_records = []
        new_barcode_records = []
        updated_alpha_records = []

        # 루프 내에서 DB 조회를 줄이기 위해 데이터 미리 준비
        for record_id in selected_records:
            barcode, modified_str = record_id.split('|')
            modified = parse_datetime(modified_str)
            alpha_record = next((alpha for alpha in barcodes_data if alpha.barcode == barcode), None)

            if alpha_record:
                # 새로운 Production_Barcode 생성
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

                # 공정에 따른 데이터 설정
                processes = []
                stop_next_processes = False  # 이후 공정으로의 진행 여부를 결정하는 플래그

                for wc_cd, pass_condition in work_centers.items():
                    if wc_cd == 'WSF70':
                        continue

                    # 이전 공정에서 불량이 발생했을 경우 이후 공정을 추가하지 않음
                    if stop_next_processes:
                        break

                    # 현재 공정 데이터 생성
                    result_value = getattr(alpha_record, pass_condition, None)
                    report_type = 'G' if result_value else 'B'

                    # 불량이면 이후 공정 중단 플래그를 설정
                    if report_type == 'B':
                        stop_next_processes = True

                    processes.append((wc_cd, report_type))

                for wc_cd, report_type in processes:
                    step_number = re.sub(r'\D', '', wc_cd)
                    item = db.session.query(Item).filter(
                        Item.ALPHA_CODE == alpha_record.product,
                        Item.SPEC.like(f'%{step_number}Step%')
                    ).first()

                    if item:
                        production_order = db.session.query(Production_Order).filter_by(ITEM_CD=item.ITEM_CD).first()
                        sl_cd = production_order.SL_CD if production_order else None

                        assn_record = {
                            'barcode': alpha_record.barcode,
                            'PRODT_ORDER_NO': None,
                            'OPR_NO': '10',
                            'REPORT_TYPE': report_type,
                            'WC_CD': wc_cd,
                            'ITEM_CD': item.ITEM_CD,
                            'CREDIT_DEBIT': 'C',
                            'MOV_TYPE': 'I01',
                            'TO_SL_CD': sl_cd,
                            'FROM_SL_CD': sl_cd,
                            'INSRT_USR': g.user.USR_ID,
                            'UPDT_USR': g.user.USR_ID
                        }
                        new_alpha_records.append(assn_record)

                # alpha 기록 업데이트 준비
                alpha_record.REPORT_FLAG = 'N'
                updated_alpha_records.append(alpha_record)

        # 데이터 일괄 삽입 및 업데이트
        if new_barcode_records:
            db.session.bulk_insert_mappings(Production_Barcode, new_barcode_records)
        if new_alpha_records:
            db.session.bulk_insert_mappings(Barcode_Flow, new_alpha_records)
        if updated_alpha_records:
            db.session.bulk_update_mappings(Production_Alpha, [record.__dict__ for record in updated_alpha_records])

        db.session.commit()
        logging.info("Database commit successful.")

        # 후속 처리 함수
        assign_production_orders()
        update_barcode_status_from_flow()
        assign_doc_no_and_material_doc()

        logging.info("Redirecting to product_register page.")
        return jsonify({"status": "success", "message": "실적 처리 완료"}), 200

    except Exception as e:
        db.session.rollback()
        logging.error(f"Database error: {str(e)}")
        return jsonify({"status": "error", "message": "데이터 처리 중 오류가 발생했습니다."}), 500

def assign_doc_no_and_material_doc():
    doc_no = generate_doc_no()

    # DOC_NO 및 ITEM_CD, PRODT_ORDER_NO, WC_CD, MOV_TYPE로 그룹화하여 QTY를 합산
    grouped_entries = db.session.query(
        Barcode_Flow.ITEM_CD,
        Barcode_Flow.PRODT_ORDER_NO,
        Barcode_Flow.WC_CD,
        Barcode_Flow.MOV_TYPE,
        Barcode_Flow.FROM_SL_CD,
        Barcode_Flow.TO_SL_CD,
        func.count(Barcode_Flow.barcode).label("total_qty")
    ).filter(
        Barcode_Flow.DOC_NO == None  # DOC_NO가 없는 항목만 대상으로
    ).group_by(
        Barcode_Flow.ITEM_CD, Barcode_Flow.PRODT_ORDER_NO, Barcode_Flow.WC_CD, Barcode_Flow.MOV_TYPE,
        Barcode_Flow.FROM_SL_CD, Barcode_Flow.TO_SL_CD
    ).all()

    new_material_docs = []
    doc_seq = 10  # 초기 SEQ 값은 10

    for entry in grouped_entries:
        item_cd, prodt_order_no, wc_cd, mov_type, from_sl_cd, to_sl_cd, total_qty = entry

        # Barcode_Flow 업데이트 (DOC_NO와 동일한 ITEM_CD에 대해 DOC_SEQ를 동일하게 설정)
        db.session.query(Barcode_Flow).filter(
            Barcode_Flow.ITEM_CD == item_cd,
            Barcode_Flow.PRODT_ORDER_NO == prodt_order_no,
            Barcode_Flow.WC_CD == wc_cd,
            Barcode_Flow.MOV_TYPE == mov_type,
            Barcode_Flow.FROM_SL_CD == from_sl_cd,
            Barcode_Flow.TO_SL_CD == to_sl_cd,
            Barcode_Flow.DOC_NO == None
        ).update(
            {'DOC_NO': doc_no, 'DOC_SEQ': doc_seq}
        )

        # Material_Doc 생성
        material_doc = {
            'DOC_NO': doc_no,
            'DOC_SEQ': f"{doc_seq:02}",  # DOC_SEQ는 두 자리로 고정
            'ITEM_CD': item_cd,
            'QTY': total_qty,  # 동일 ITEM_CD의 QTY 합산
            'CREDIT_DEBIT': 'C',  # 기본값 설정
            'OPR_NO': '10',
            'REPORT_TYPE': 'G',
            'PRODT_ORDER_NO': prodt_order_no,
            'WC_CD': wc_cd,
            'MOV_TYPE': mov_type,
            'FROM_SL_CD': from_sl_cd,  # FROM_SL_CD 추가
            'TO_SL_CD': to_sl_cd,  # TO_SL_CD 추가
            'INSRT_DT': datetime.now(),
            'INSRT_USR': g.user.USR_ID,
            'UPDT_DT': datetime.now(),  # 업데이트 시각 설정
            'UPDT_USR': g.user.USR_ID
        }
        new_material_docs.append(material_doc)

        # 다음 ITEM_CD에 대해 DOC_SEQ를 10씩 증가
        doc_seq += 10

    # Material_Doc에 데이터 삽입
    if new_material_docs:
        db.session.bulk_insert_mappings(Material_Doc, new_material_docs)


    db.session.commit()
    logging.info("DOC_NO와 Material_Doc 데이터가 성공적으로 할당되었습니다.")

def update_barcode_status_from_flow():
    # 최신의 REPORT_TYPE을 기반으로 데이터 가져옴
    latest_flows = db.session.query(
        Barcode_Flow.barcode,
        Barcode_Flow.ITEM_CD,
        Barcode_Flow.WC_CD,
        Barcode_Flow.REPORT_TYPE,
        func.max(Barcode_Flow.INSRT_DT).label("latest_insert")
    ).group_by(Barcode_Flow.barcode, Barcode_Flow.ITEM_CD, Barcode_Flow.WC_CD, Barcode_Flow.REPORT_TYPE).all()

    for flow in latest_flows:
        barcode = flow.barcode
        item_cd = flow.ITEM_CD
        wc_cd = flow.WC_CD
        report_type = flow.REPORT_TYPE

        # Status 코드 매핑
        if wc_cd == 'WSF40':
            status_cd = 'P4' if report_type == 'G' else 'E4'
        elif wc_cd == 'WSF50':
            status_cd = 'P5' if report_type == 'G' else 'E5'
        elif wc_cd == 'WSF60':
            status_cd = 'P6' if report_type == 'G' else 'E6'
        else:
            # 해당하는 작업 센터 코드가 없는 경우는 건너뜀
            continue

        # Barcode_Status에서 해당 barcode를 조회하여 존재 여부 확인
        status_record = db.session.query(Barcode_Status).filter(Barcode_Status.barcode == barcode).first()

        if status_record:
            # 기존 레코드가 있을 경우 STATUS와 ITEM_CD 업데이트
            status_record.STATUS = status_cd
            status_record.ITEM_CD = item_cd
            logging.info(f"Updated Barcode_Status for barcode={barcode} with STATUS={status_cd}, ITEM_CD={item_cd}")
        else:
            # 새 레코드를 추가하는 경우
            new_status_record = Barcode_Status(barcode=barcode, STATUS=status_cd, ITEM_CD=item_cd)
            db.session.add(new_status_record)
            logging.info(f"Inserted new Barcode_Status for barcode={barcode} with STATUS={status_cd}, ITEM_CD={item_cd}")

    db.session.commit()
    logging.info("Barcode_Status update commit successful.")

def assign_production_orders():
    work_centers = db.session.query(Work_Center.WC_CD).all()
    barcodes = db.session.query(Barcode_Flow, Production_Barcode.product).join(
        Production_Barcode, Barcode_Flow.barcode == Production_Barcode.barcode
    ).filter(
        Barcode_Flow.PRODT_ORDER_NO == None
    ).all()

    orders = {wc_cd: {} for wc_cd, in work_centers}
    unmatched_barcodes = []  # 매칭되지 않은 바코드 수집

    # 각 작업 센터별 오더 생성
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

    order_indices = {wc_cd: {} for wc_cd in orders.keys()}
    assn_records = []
    updated_alpha_records = []

    # 바코드 매칭
    for barcode_assign, barcode_product in barcodes:
        wc_cd = barcode_assign.WC_CD
        if wc_cd == 'WSF70':  # 'WSF70' 공정은 매칭 과정 제외
            continue

        if wc_cd in orders and barcode_product in orders[wc_cd]:
            order_list = orders[wc_cd][barcode_product]

            if barcode_product not in order_indices[wc_cd]:
                order_indices[wc_cd][barcode_product] = 0

            order = order_list[order_indices[wc_cd][barcode_product]]

            if isinstance(order, Production_Order):
                barcode_assign.PRODT_ORDER_NO = order.PRODT_ORDER_NO
                if barcode_assign.REPORT_TYPE == 'G':
                    order.PROD_QTY_IN_ORDER_UNIT += 1
                else:
                    order.BAD_QTY_IN_ORDER_UNIT += 1

                if (order.PROD_QTY_IN_ORDER_UNIT + order.BAD_QTY_IN_ORDER_UNIT) >= order.PRODT_ORDER_QTY:
                    order.ORDER_STATUS = 'CL'
                    order_indices[wc_cd][barcode_product] += 1
                    if order_indices[wc_cd][barcode_product] >= len(order_list):
                        order_indices[wc_cd][barcode_product] = len(order_list) - 1

                barcode_assign.INSRT_USR = g.user.USR_ID
                barcode_assign.UPDT_USR = g.user.USR_ID

                if barcode_assign.PRODT_ORDER_NO is not None:
                    assn_records.append(barcode_assign)

                alpha_record = Production_Alpha.query.filter_by(barcode=barcode_assign.barcode).first()
                if alpha_record:
                    alpha_record.REPORT_FLAG = 'Y'
                    updated_alpha_records.append(alpha_record)
        else:
            # 매칭되지 않은 바코드 수집
            unmatched_barcodes.append(barcode_assign.barcode)
            alpha_record = Production_Alpha.query.filter_by(barcode=barcode_assign.barcode).first()
            if alpha_record:
                alpha_record.REPORT_FLAG = 'N'
                updated_alpha_records.append(alpha_record)

    # 매칭되지 않은 바코드 삭제
    db.session.query(Barcode_Flow).filter(
        Barcode_Flow.PRODT_ORDER_NO == None
    ).delete(synchronize_session=False)

    # 바코드와 alpha 기록 업데이트
    if assn_records:
        db.session.bulk_update_mappings(Barcode_Flow, [record.__dict__ for record in assn_records])

    if updated_alpha_records:
        db.session.bulk_update_mappings(Production_Alpha, [record.__dict__ for record in updated_alpha_records])

    db.session.commit()

    # 매칭되지 않은 바코드 정보를 세션에 저장하여 사용자에게 알림
    if unmatched_barcodes:
        session['unmatched_barcodes'] = unmatched_barcodes
        flash(f"제조오더번호와 매칭되지 않은 바코드가 있습니다: {', '.join(unmatched_barcodes)}", "warning")

    # 생산 결과 저장
    insert_production_results(orders)

def insert_production_results(orders):
    result_records = []

    for wc_cd in orders.keys():
        # 70 공정 제외
        if wc_cd == 'WSF70':
            continue

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

def generate_doc_no():
    # 오늘 날짜에 기반한 doc_no 접두사 설정
    today_prefix = datetime.now().strftime('%Y%m%d')
    doc_prefix = f"DOC{today_prefix}"

    # 가장 최근 doc_no 조회
    max_doc_no = db.session.query(func.max(Material_Doc.DOC_NO)).filter(
        Material_Doc.DOC_NO.like(f"{doc_prefix}%")
    ).scalar()

    # 새로운 doc_no 생성: 가장 최근 번호에 +1
    if max_doc_no:
        last_number = int(max_doc_no[-5:])  # doc_no의 마지막 5자리 숫자를 추출
        new_number = last_number + 1
    else:
        new_number = 1  # 오늘 처음 생성되는 경우 1로 시작

    new_doc_no = f"{doc_prefix}{new_number:05d}"  # 5자리 연속번호로 구성
    return new_doc_no

def update_barcode_status_after_packing(doc_no):
    # DOC_NO에 해당하는 모든 바코드
    barcodes = db.session.query(Barcode_Flow.barcode).filter(
        Barcode_Flow.DOC_NO == doc_no
    ).distinct().all()

    for barcode_tuple in barcodes:
        barcode = barcode_tuple[0]

        # 특정 바코드의 최신 레코드 가져오기 (가장 최근 INSRT_DT)
        latest_flow = db.session.query(
            Barcode_Flow.barcode,
            Barcode_Flow.ITEM_CD,
            Barcode_Flow.WC_CD,
            Barcode_Flow.BOX_NUM
        ).filter(
            Barcode_Flow.barcode == barcode
        ).order_by(Barcode_Flow.INSRT_DT.desc()).first()

        if latest_flow:
            item_cd = latest_flow.ITEM_CD
            box_num = latest_flow.BOX_NUM

            # BOX_NUM이 존재하면 상태 코드를 'P7'로 설정
            if box_num:
                status_cd = 'P7'
            else:
                # WC_CD에 따라 상태 코드를 설정
                if latest_flow.WC_CD == 'WSF40':
                    status_cd = 'p4'
                elif latest_flow.WC_CD == 'WSF50':
                    status_cd = 'p5'
                elif latest_flow.WC_CD == 'WSF60':
                    status_cd = 'p6'
                else:
                    # 해당 공정 코드가 없는 경우 건너뜀
                    continue

            # Barcode_Status에서 해당 barcode를 조회하여 존재 여부 확인
            status_record = db.session.query(Barcode_Status).filter(
                Barcode_Status.barcode == barcode
            ).first()

            if status_record:
                # 기존 레코드가 있을 경우 STATUS, ITEM_CD, BOX_NUM 업데이트
                status_record.STATUS = status_cd
                status_record.ITEM_CD = item_cd
                status_record.BOX_NUM = box_num
                logging.info(
                    f"Updated Barcode_Status for barcode={barcode} with STATUS={status_cd}, ITEM_CD={item_cd}, BOX_NUM={box_num}"
                )
            else:
                # 새 레코드를 추가하는 경우
                new_status_record = Barcode_Status(
                    barcode=barcode, STATUS=status_cd, ITEM_CD=item_cd, BOX_NUM=box_num
                )
                db.session.add(new_status_record)
                logging.info(
                    f"Inserted new Barcode_Status for barcode={barcode} with STATUS={status_cd}, ITEM_CD={item_cd}, BOX_NUM={box_num}"
                )

    db.session.commit()
    logging.info("Barcode_Status update after packing commit successful.")


@bp.route('/assign-orders', methods=['POST'])
def assign_orders_route():
    assign_production_orders()
    return '<script>alert("생산 오더가 할당되었습니다."); window.location.href="/product/assign/";</script>'

# 제조오더랑 관련 없이 그냥 바로 바코드 스캔하고 그 데이터로 박스번호생성
@bp.route('/register_result_packing/', methods=['GET', 'POST'])
def product_register_packing():
    m_box_no = request.form.get('m_box_no', '')
    cs_model = request.form.get('cs_model', '')

    # Packing_Cs 모델에서 데이터를 조회
    query = db.session.query(Packing_Cs)

    # 검색 조건 추가
    if m_box_no:
        query = query.filter(Packing_Cs.m_box_no == m_box_no)
    if cs_model:
        query = query.filter(Packing_Cs.cs_model == cs_model)

    packing_cs_data = query.all()

    return render_template(
        'product/product_register_packing.html',
        packing_cs_data=packing_cs_data,
        m_box_no=m_box_no,
        cs_model=cs_model
    )

# 바코드 스캔 데이터 검증 로직
@bp.route('/check_barcode/', methods=['POST'])
def check_barcode():
    barcode = request.json.get('barcode')
    if not barcode:
        return jsonify({"status": "error", "message": "Barcode is required"}), 400

    # 기존 Production_Barcode_Assign 검증 로직 유지
    barcode_data = db.session.query(Barcode_Flow).filter(
        Barcode_Flow.barcode == barcode,
        Barcode_Flow.WC_CD == 'WSF60',
        Barcode_Flow.REPORT_TYPE == 'G'
    ).first()
    print(f"Received barcode: {barcode}")

    # 이미 박스 번호와 매칭된 바코드인지 확인
    existing_match = db.session.query(Barcode_Flow).filter(
        Barcode_Flow.barcode == barcode,
        Barcode_Flow.BOX_NUM.isnot(None)  # 이미 박스 번호와 매칭된 바코드인지 확인
    ).first()

    if existing_match:
        return jsonify({"status": "error", "message": "Barcode is already assigned to a box"}), 400

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
    # 오늘 날짜를 기반으로 새로운 박스 번호 생성
    today = datetime.today()
    date_hex = date_to_hex(today)

    # 오늘 날짜에 해당하는 마스터 박스 번호 중 가장 큰 값 조회 및 증가 처리
    max_master_box_no = db.session.query(func.max(Packing_Cs.m_box_no)).filter(
        Packing_Cs.m_box_no.like(f"{date_hex}%")
    ).scalar()

    if max_master_box_no:
        # 마지막 3자리 숫자 추출 후 +1 증가
        last_sequence = int(max_master_box_no[-3:])
        new_sequence = last_sequence + 1
    else:
        new_sequence = 1  # 처음 생성되는 경우 1로 시작

    # 새로운 마스터 박스 번호 생성 (예: '7E912001')
    new_master_box_no = f"{date_hex}{new_sequence:03}"

    return jsonify({"status": "success", "next_master_box_no": new_master_box_no})

def date_to_hex(date_obj):
    year = date_obj.year % 100  # 마지막 두 자리만 사용
    month = date_obj.month
    day = date_obj.day
    return f"{year:02X}{month:02X}{day:02X}"  # 16진수로 변환

# 데이터 db에 insert
@bp.route('/save_packing_data/', methods=['POST'])
def save_packing_data():
    try:
        data = request.json
        logging.info(f"Received packing data: {data}")

        # 데이터 유효성 검사
        if not data or 'lot_no' not in data or 'quantity' not in data or 'expiry_date' not in data:
            return jsonify({"status": "error", "message": "Missing required data fields"}), 400

        # Master Box 번호 생성
        master_box_no_response = get_next_master_box_no()
        master_box_no = master_box_no_response.json.get("next_master_box_no")
        if not master_box_no:
            return jsonify({"status": "error", "message": "Failed to generate master box number"}), 500

        lot_no = data['lot_no']
        quantity = data['quantity']
        expiry_date = datetime.strptime(data['expiry_date'], '%Y-%m-%d')

        # Packing_Dtl 및 Packing_Cs 테이블에 데이터 추가
        for row in data['rows']:
            barcode = row['udi_qr'][:-1]
            udi_code = row['barcode']

            # Packing_Dtl 생성
            packing_detail = Packing_Dtl(
                m_box_no=master_box_no,
                lot_no=lot_no,
                barcode=barcode,
                udi_code=udi_code,
                packing_dt=datetime.now(),
                exp_date=expiry_date
            )
            db.session.add(packing_detail)

            # Barcode_Flow 로직 업데이트 (이전 데이터 기반으로 새 데이터 추가)
            last_row = db.session.query(Barcode_Flow).filter_by(barcode=barcode).order_by(
                Barcode_Flow.id.desc()).first()
            if last_row and last_row.WC_CD == 'WSF60':
                new_barcode_flow = Barcode_Flow(
                    barcode=barcode,
                    ITEM_CD=last_row.ITEM_CD,
                    WC_CD=None,
                    FROM_SL_CD=last_row.TO_SL_CD,
                    TO_SL_CD='SF40',
                    MOV_TYPE='T01',
                    CREDIT_DEBIT='C',
                    REPORT_TYPE='G',
                    BOX_NUM=master_box_no,  # Master Box 번호 추가
                    INSRT_DT=datetime.now(),
                    INSRT_USR=g.user.USR_ID,
                    UPDT_USR=g.user.USR_ID
                )
                db.session.add(new_barcode_flow)

        # Barcode_Flow에서 ITEM_CD 조회
        if last_row:
            item_cd = last_row.ITEM_CD

            # Item 모델에서 cs_model과 cs_udi_di 정보 조회
            item_data = db.session.query(Item).filter_by(ITEM_CD=item_cd).first()
            if item_data:
                cs_model = item_cd
                cs_udi_di = item_data.UDI_CODE
            else:
                return jsonify({"status": "error", "message": "Item data not found for the given ITEM_CD"}), 400

            # Packing_Cs 생성
            packing_cs = Packing_Cs(
                prodt_order_no=None,
                cs_model=cs_model,
                m_box_no=master_box_no,
                cs_qty=quantity,
                cs_lot_no=lot_no,
                cs_udi_di=cs_udi_di,
                cs_udi_lotno=lot_no,
                cs_udi_prod=datetime.now().strftime('%Y%m%d'),
                cs_prod_date=datetime.now().strftime('%Y%m%d'),
                cs_exp_date=expiry_date.strftime('%Y%m%d'),
                cs_udi_qr=f"01{cs_udi_di}10{master_box_no}11{datetime.now().strftime('%Y%m%d')}17{expiry_date.strftime('%Y%m%d')}",
                print_flag="N"
            )
            db.session.add(packing_cs)

        # 모든 데이터가 들어간 후 DOC_NO 및 Material_Doc 데이터 추가
        db.session.commit()
        assign_doc_no_and_material_doc_packing(master_box_no)

        return jsonify({"status": "success", "message": "Packing data saved successfully"})
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error saving packing data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def assign_doc_no_and_material_doc_packing(master_box_no):
    # 새로운 DOC_NO 생성
    doc_no = generate_doc_no()

    # DOC_NO 및 ITEM_CD, PRODT_ORDER_NO, MOV_TYPE로 그룹화하여 QTY를 합산
    grouped_entries = db.session.query(
        Barcode_Flow.ITEM_CD,
        Barcode_Flow.PRODT_ORDER_NO,
        Barcode_Flow.MOV_TYPE,
        Barcode_Flow.FROM_SL_CD,
        Barcode_Flow.TO_SL_CD,
        func.count(Barcode_Flow.barcode).label("total_qty")
    ).filter(
        Barcode_Flow.DOC_NO == None
    ).group_by(
        Barcode_Flow.ITEM_CD, Barcode_Flow.PRODT_ORDER_NO, Barcode_Flow.MOV_TYPE,
        Barcode_Flow.FROM_SL_CD, Barcode_Flow.TO_SL_CD
    ).all()

    new_material_docs = []
    doc_seq = 10

    for entry in grouped_entries:
        item_cd, prodt_order_no, mov_type, from_sl_cd, to_sl_cd, total_qty = entry

        # Barcode_Flow 업데이트
        db.session.query(Barcode_Flow).filter(
            Barcode_Flow.ITEM_CD == item_cd,
            Barcode_Flow.PRODT_ORDER_NO == prodt_order_no,
            Barcode_Flow.MOV_TYPE == mov_type,
            Barcode_Flow.FROM_SL_CD == from_sl_cd,
            Barcode_Flow.TO_SL_CD == to_sl_cd,
            Barcode_Flow.DOC_NO == None
        ).update(
            {'DOC_NO': doc_no, 'DOC_SEQ': doc_seq}
        )

        # Material_Doc 생성
        material_doc = {
            'DOC_NO': doc_no,
            'DOC_SEQ': f"{doc_seq:02}",
            'ITEM_CD': item_cd,
            'QTY': total_qty,
            'CREDIT_DEBIT': 'C',
            'OPR_NO': None,
            'REPORT_TYPE': 'G',
            'PRODT_ORDER_NO': prodt_order_no,
            'BOX_NUM': master_box_no,  # 박스 번호 전달
            'MOV_TYPE': mov_type,
            'FROM_SL_CD': from_sl_cd,  # FROM_SL_CD 추가
            'TO_SL_CD': to_sl_cd,  # TO_SL_CD 추가
            'INSRT_DT': datetime.now(),
            'INSRT_USR': g.user.USR_ID,
            'UPDT_DT': datetime.now(),
            'UPDT_USR': g.user.USR_ID
        }
        new_material_docs.append(material_doc)
        doc_seq += 10

    # Material_Doc에 데이터 삽입
    if new_material_docs:
        db.session.bulk_insert_mappings(Material_Doc, new_material_docs)

    db.session.commit()
    update_barcode_status_after_packing(doc_no)
    logging.info("Packing용 DOC_NO와 Material_Doc 데이터가 성공적으로 할당되었습니다.")


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

# 멸균반제품 반출등록 렌더링
@bp.route('/register_sterilizating_out/', methods=['GET', 'POST'])
def product_register_sterilizating_out():
    # 조회 조건
    insrt_dt_start = request.form.get('start_date', datetime.now().strftime('%Y-%m-%d'))

    # Barcode_Flow에서 TO_SL_CD가 "SF40"인 데이터들의 BOX_NUM 조회 (왼쪽 테이블)
    left_barcode_query = db.session.query(Barcode_Flow.BOX_NUM).filter(Barcode_Flow.TO_SL_CD == 'SF40').distinct()
    left_box_numbers = [box_num[0] for box_num in left_barcode_query.all()]

    # Barcode_Flow에서 FROM_SL_CD가 "SF40"인 데이터들의 BOX_NUM 조회 (오른쪽 테이블)
    right_barcode_query = db.session.query(
        Barcode_Flow.BOX_NUM,
        Barcode_Flow.INSRT_DT  # INSRT_DT를 추가로 가져옴
    ).filter(
        Barcode_Flow.FROM_SL_CD == 'SF40',
        cast(Barcode_Flow.INSRT_DT, Date) >= insrt_dt_start
    ).distinct()
    right_box_data = right_barcode_query.all()
    right_box_numbers = [box_data[0] for box_data in right_box_data]

    # 이미 반출 등록된 박스 번호 조회 (FROM_SL_CD='SF40'인 데이터)
    already_registered_boxes = db.session.query(Barcode_Flow.BOX_NUM).filter(
        Barcode_Flow.FROM_SL_CD == 'SF40'
    ).distinct()
    already_registered_box_numbers = {box_num[0] for box_num in already_registered_boxes}

    # 오른쪽 테이블과 이미 등록된 박스번호를 제외한 데이터 필터링 (왼쪽 테이블)
    unique_left_box_numbers = set(left_box_numbers) - set(right_box_numbers) - already_registered_box_numbers

    # Packing_Cs에서 M_BOX_NO가 unique_left_box_numbers에 포함된 데이터 조회
    left_table_data = db.session.query(
        Packing_Cs.cs_model,
        Packing_Cs.m_box_no,
        Packing_Cs.cs_qty,
        Packing_Cs.cs_prod_date,
        Item.ITEM_NM.label('item_name')  # Item의 ITEM_NM 가져오기
    ).join(
        Item, Packing_Cs.cs_model == Item.ITEM_CD  # cs_model과 Item의 ITEM_CD 조인
    ).filter(
        Packing_Cs.m_box_no.in_(unique_left_box_numbers)
    ).all()

    # Packing_Cs에서 M_BOX_NO가 right_box_numbers에 포함된 데이터 조회 (오른쪽 테이블)
    right_table_data = db.session.query(
        Packing_Cs.cs_model,
        Packing_Cs.m_box_no,
        Packing_Cs.cs_qty,
        Packing_Cs.cs_prod_date,
        Item.ITEM_NM.label('item_name')  # Item의 ITEM_NM 가져오기
    ).join(
        Item, Packing_Cs.cs_model == Item.ITEM_CD  # cs_model과 Item의 ITEM_CD 조인
    ).filter(
        Packing_Cs.m_box_no.in_(right_box_numbers)
    ).all()

    # INSRT_DT 값을 Packing_Cs 데이터와 매핑
    right_table_with_insrt_dt = [
        {
            "cs_model": row.cs_model,
            "m_box_no": row.m_box_no,
            "cs_qty": row.cs_qty,
            "cs_prod_date": row.cs_prod_date,
            "item_name": row.item_name,
            "insrt_dt": (
                box[1].strftime('%Y%m%d') if box[1] else None  # INSRT_DT를 "YYYYMMDD" 형식으로 변환
            )
        }
        for row in right_table_data
        for box in right_box_data if box[0] == row.m_box_no
    ]

    return render_template(
        'product/product_register_sterilizating_out.html',
        packing_cs_data=left_table_data,  # 왼쪽 테이블 데이터 전달
        right_packing_cs_data=right_table_with_insrt_dt,  # 오른쪽 테이블 데이터 전달
        INSRT_DT_START=insrt_dt_start  # 기본 조회 날짜 전달
    )

# 멸균반제품 반출시 모달에 대한 박스 QR 체크 로직 라우트 함수
@bp.route('/get_packing_cs_data/', methods=['POST'])
def get_packing_cs_data():
    try:
        request_data = request.get_json()
        print(f"Request Data: {request_data}")  # 로그 추가

        udi_qr = request_data.get('udi_qr')
        print(f"Received UDI QR: {udi_qr}")  # 로그 추가

        if not udi_qr or len(udi_qr) != 47:
            print("Invalid QR Code Length or Missing QR Code")  # 에러 로그
            return jsonify({'status': 'error', 'message': 'QR 코드가 유효하지 않습니다. 47자리를 입력하세요.'}), 400

        packing_cs_data = db.session.query(
            Packing_Cs.m_box_no,
            Packing_Cs.cs_model,
            Packing_Cs.cs_qty,
            Packing_Cs.cs_prod_date
        ).filter(Packing_Cs.cs_udi_qr == udi_qr).first()
        print(f"Fetched Packing_Cs Data: {packing_cs_data}")  # 데이터 조회 로그

        if not packing_cs_data:
            print(f"No Data Found for QR Code: {udi_qr}")  # 데이터 없음 로그
            return jsonify({'status': 'error', 'message': '해당 QR 코드에 대한 데이터를 찾을 수 없습니다.'}), 404

        print(f"QR Code {udi_qr} added to scanned list.")  # 성공 로그

        return jsonify({
            'status': 'success',
            'packing_cs': {
                'm_box_no': packing_cs_data.m_box_no,
                'cs_model': packing_cs_data.cs_model,
                'cs_qty': int(packing_cs_data.cs_qty),
                'cs_prod_date': packing_cs_data.cs_prod_date
            }
        })

    except Exception as e:
        print(f"Error in get_packing_cs_data: {e}")  # 에러 로그
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

# BARCODE FLOW에 멸균외주 출하 데이터 넣기 + MATERIAL_DOC 데이터 생성및 DCO_NO 부여
@bp.route('/register_outsourced_packing/', methods=['POST'])
def register_outsourced_packing():
    try:
        data = request.json
        logging.info(f"Received data for outsourced packing: {data}")

        # 데이터 유효성 검사
        if not data or 'rows' not in data:
            return jsonify({"status": "error", "message": "No rows provided for processing"}), 400

        for row in data['rows']:
            m_box_no = row.get('m_box_no') or row.get('box_no')

            if not m_box_no:
                logging.warning("Missing m_box_no in the request row.")
                continue

            # Barcode_Flow에서 m_box_no와 관련된 barcode 조회
            barcodes = db.session.query(Barcode_Flow).filter_by(BOX_NUM=m_box_no).all()

            if not barcodes:
                logging.warning(f"No barcodes found for m_box_no: {m_box_no}")
                continue

            for barcode_entry in barcodes:
                # Barcode_Flow의 기존 데이터 기반으로 새로운 데이터 생성
                new_barcode_flow = Barcode_Flow(
                    barcode=barcode_entry.barcode,
                    ITEM_CD=barcode_entry.ITEM_CD,
                    WC_CD=None,
                    FROM_SL_CD=barcode_entry.TO_SL_CD,
                    TO_SL_CD='WO00061',  # 외주 창고 코드
                    MOV_TYPE='T01',
                    CREDIT_DEBIT='C',
                    REPORT_TYPE='G',
                    BP_CD='O00061', # 그린피아기술
                    BOX_NUM=m_box_no,
                    INSRT_DT=datetime.now(),
                    INSRT_USR=g.user.USR_ID,
                    UPDT_USR=g.user.USR_ID
                )
                db.session.add(new_barcode_flow)

        # 새로운 DOC_NO 생성 및 Material_Doc 추가
        doc_no = generate_doc_no()

        # Barcode_Flow에서 박스별 그룹화하여 ITEM_CD, PRODT_ORDER_NO 등의 데이터 준비
        grouped_entries = db.session.query(
            Barcode_Flow.BOX_NUM,
            Barcode_Flow.ITEM_CD,
            Barcode_Flow.PRODT_ORDER_NO,
            Barcode_Flow.MOV_TYPE,
            Barcode_Flow.FROM_SL_CD,
            Barcode_Flow.BP_CD,
            Barcode_Flow.TO_SL_CD,
            func.count(Barcode_Flow.barcode).label("total_qty")
        ).filter(
            Barcode_Flow.BOX_NUM.in_([row.get('box_no') for row in data['rows']]),
            Barcode_Flow.DOC_NO == None  # 이미 처리된 데이터는 제외
        ).group_by(
            Barcode_Flow.BOX_NUM,  # 박스 번호 기준 추가
            Barcode_Flow.ITEM_CD,
            Barcode_Flow.PRODT_ORDER_NO,
            Barcode_Flow.MOV_TYPE,
            Barcode_Flow.FROM_SL_CD,
            Barcode_Flow.BP_CD,
            Barcode_Flow.TO_SL_CD
        ).all()

        doc_seq = 10
        new_material_docs = []

        # 그룹화된 데이터를 기반으로 Material_Doc 생성 및 Barcode_Flow 업데이트
        for entry in grouped_entries:
            box_num, item_cd, prodt_order_no, mov_type, from_sl_cd, bp_cd, to_sl_cd, total_qty = entry

            # Material_Doc 데이터 준비
            material_doc = {
                'DOC_NO': doc_no,
                'DOC_SEQ': f"{doc_seq:02}",
                'ITEM_CD': item_cd,
                'QTY': total_qty,
                'CREDIT_DEBIT': 'C',
                'OPR_NO': None,
                'REPORT_TYPE': 'G',
                'PRODT_ORDER_NO': prodt_order_no,
                'BOX_NUM': box_num,  # 박스 번호 추가
                'MOV_TYPE': mov_type,
                'FROM_SL_CD': from_sl_cd,
                'TO_SL_CD': to_sl_cd,
                'BP_CD': bp_cd,
                'INSRT_DT': datetime.now(),
                'INSRT_USR': g.user.USR_ID,
                'UPDT_DT': datetime.now(),
                'UPDT_USR': g.user.USR_ID
            }
            new_material_docs.append(material_doc)

            # Barcode_Flow DOC_NO 업데이트
            db.session.query(Barcode_Flow).filter(
                Barcode_Flow.ITEM_CD == item_cd,
                Barcode_Flow.PRODT_ORDER_NO == prodt_order_no,
                Barcode_Flow.MOV_TYPE == mov_type,
                Barcode_Flow.FROM_SL_CD == from_sl_cd,
                Barcode_Flow.TO_SL_CD == to_sl_cd,
                Barcode_Flow.BOX_NUM == box_num,  # 특정 박스 번호만 업데이트
                Barcode_Flow.DOC_NO == None
            ).update({'DOC_NO': doc_no, 'DOC_SEQ': doc_seq})

            doc_seq += 10

        # Material_Doc에 데이터 삽입
        if new_material_docs:
            db.session.bulk_insert_mappings(Material_Doc, new_material_docs)

        # Barcode_Status 업데이트
        update_barcode_status_after_sterilizating_out(doc_no)

        # 변경사항 커밋
        db.session.commit()

        return jsonify({"status": "success", "message": f"멸균외주 출하등록 및 전표생성 완료: {doc_no}"})

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error registering outsourced packing data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# BARCODE_STATUS 업데이트 -> 멸균 출하
def update_barcode_status_after_sterilizating_out(doc_no):
    try:
        # DOC_NO에 해당하는 모든 바코드 가져오기
        barcodes = db.session.query(Barcode_Flow.barcode).filter(
            Barcode_Flow.DOC_NO == doc_no,
            Barcode_Flow.FROM_SL_CD == 'SF40'  # FROM_SL_CD가 SF40인 조건 추가
        ).distinct().all()

        # 바코드 목록 추출
        barcode_list = [barcode_tuple[0] for barcode_tuple in barcodes]

        if not barcode_list:
            logging.info(f"No barcodes found with DOC_NO={doc_no} and FROM_SL_CD='SF40'.")
            return

        # Barcode_Status 업데이트
        for barcode in barcode_list:
            # Barcode_Status에서 해당 바코드 조회
            status_record = db.session.query(Barcode_Status).filter(
                Barcode_Status.barcode == barcode
            ).first()

            if status_record:
                # 기존 레코드가 있으면 상태를 "S9"로 업데이트
                status_record.STATUS = 'S9'
                logging.info(f"Updated Barcode_Status for barcode={barcode} to STATUS='S9'.")
            else:
                # 레코드가 없으면 새로 생성
                new_status_record = Barcode_Status(
                    barcode=barcode,
                    STATUS='S9'
                )
                db.session.add(new_status_record)
                logging.info(f"Inserted new Barcode_Status for barcode={barcode} with STATUS='S9'.")

        # 변경사항 커밋
        db.session.commit()
        logging.info("Barcode_Status successfully updated to 'S9' for all relevant barcodes.")

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating Barcode_Status: {str(e)}")
        raise

# BARCODE FLOW에 멸균외주 출하데이터 barcode 데이터 추적
@bp.route('/get_barcodes_by_box/', methods=['POST'])
def get_barcodes_by_box():
    try:
        # 클라이언트에서 전달받은 데이터
        data = request.json
        logging.info(f"Received request for barcodes by box: {data}")

        if not data or 'm_box_no' not in data:  # m_box_no는 Packing_Cs의 필드
            return jsonify({"status": "error", "message": "Missing 'm_box_no' field"}), 400

        box_num = data['m_box_no']  # m_box_no와 box_num이 동일하므로 변환

        # Barcode_Flow에서 box_num과 관련된 barcode 조회
        barcodes = db.session.query(Barcode_Flow.barcode).filter_by(BOX_NUM=box_num).all()

        if not barcodes:
            return jsonify({"status": "error", "message": f"No barcodes found for m_box_no {box_num}"}), 404

        # 바코드 목록을 클라이언트로 반환
        barcode_list = [b.barcode for b in barcodes]
        logging.info(f"Barcodes for m_box_no {box_num}: {barcode_list}")

        return jsonify({"status": "success", "barcodes": barcode_list})

    except Exception as e:
        logging.error(f"Error fetching barcodes by box: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# 멸균반제품 반출 결과 조회 렌더링 (doc 기준)
@bp.route('/result_sterilizating_out/', methods=['GET', 'POST'])
def product_result_sterilizating_out():
    # 검색 조건 받아오기
    plant_code = request.form.get('plant_code', '').strip()
    from_sl_cd = request.form.get('from-sl-cd', 'SF40').strip()
    to_sl_cd = request.form.get('to-sl-cd', '').strip()
    start_date = request.form.get('start_date', datetime.now().strftime('%Y-%m-%d')).strip()

    # 기본 쿼리 작성
    query = (
        db.session.query(
            Material_Doc.DOC_NO,
            Material_Doc.DOC_SEQ,
            Material_Doc.ITEM_CD,
            Item.ITEM_NM,
            Material_Doc.BP_CD,
            Biz_Partner.bp_nm,
            Item.BASIC_UNIT,
            Material_Doc.QTY,
            Material_Doc.BOX_NUM,
            Material_Doc.INSRT_DT
        )
        .join(Item, Material_Doc.ITEM_CD == Item.ITEM_CD, isouter=True)
        .join(Biz_Partner, Material_Doc.BP_CD == Biz_Partner.bp_cd, isouter=True)
    )

    query = query.filter(Material_Doc.FROM_SL_CD == 'SF40')

    # 검색 조건 적용
    if plant_code:
        query = query.filter(Material_Doc.PLANT_CD == plant_code)
    if to_sl_cd:
        query = query.filter(Material_Doc.TO_SL_CD == to_sl_cd)
    if start_date:
        query = query.filter(cast(Material_Doc.INSRT_DT, Date) >= start_date)

    # 결과 조회
    orders_with_hdr = query.order_by(Material_Doc.DOC_NO, Material_Doc.DOC_SEQ).all()

    # 템플릿 렌더링
    return render_template(
        'product/product_result_sterilizating_out.html',
        orders_with_hdr=orders_with_hdr,
        INSRT_DT_START=start_date,
        form_submitted=True
    )

# 멸균제품 입고등록 렌더링
@bp.route('/register_sterilizating_in/', methods=['GET', 'POST'])
def product_register_sterilizating_in():
    # 검색 조건 처리
    plant_code = request.form.get('plant_code', '').strip()
    start_date = request.form.get('start_date', datetime.now().strftime('%Y-%m-%d'))
    end_date = request.form.get('end_date', datetime.now().strftime('%Y-%m-%d'))

    today = datetime.now()
    start_date = request.form.get('start_date', (today - timedelta(days=15)).strftime('%Y-%m-%d'))
    end_date = request.form.get('end_date', (today + timedelta(days=15)).strftime('%Y-%m-%d'))

    # 기본 날짜 변환
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1, seconds=-1)  # 하루 끝까지 포함

    # 서브쿼리: Barcode_Flow에서 TO_SL_CD가 'SF32'인 박스번호 추출
    subquery_sf32 = db.session.query(Barcode_Flow.BOX_NUM).filter(
        Barcode_Flow.TO_SL_CD == 'SF32'
    ).subquery()

    # Packing_Cs와 Barcode_Flow를 JOIN하여 TO_SL_CD가 'WO00061'인 데이터만 조회 (왼쪽 테이블)
    left_table_query = db.session.query(
        Packing_Cs.m_box_no.label("box_num"),  # Packing_Cs의 박스 번호 가져오기
        Barcode_Flow.ITEM_CD.label("item_cd"),
        Item.ITEM_NM.label("item_name"),
        Packing_Cs.cs_qty.label("qty"),  # Packing_Cs의 수량 가져오기
        Packing_Cs.cs_prod_date.label("prod_date"),  # Packing_Cs의 포장일자 가져오기
        Barcode_Flow.INSRT_DT.label("insrt_dt")  # Barcode_Flow의 삽입일자
    ).join(
        Barcode_Flow, Packing_Cs.m_box_no == Barcode_Flow.BOX_NUM  # Packing_Cs와 Barcode_Flow JOIN
    ).join(
        Item, Barcode_Flow.ITEM_CD == Item.ITEM_CD  # 품목 연결
    ).filter(
        Barcode_Flow.TO_SL_CD == 'WO00061',  # TO_SL_CD가 'WO00061'인 데이터만
        ~Packing_Cs.m_box_no.in_(subquery_sf32),  # TO_SL_CD='SF32'에 해당하지 않는 박스번호만
        Barcode_Flow.INSRT_DT.between(start_date, end_date)  # 삽입일자 필터링
    ).distinct(
        Packing_Cs.m_box_no  # DISTINCT 기준 컬럼 설정
    ).all()

    # 결과 데이터 포맷 (왼쪽 테이블)
    left_table_data = [
        {
            "box_num": row.box_num,  # Packing_Cs의 박스 번호 사용
            "item_cd": row.item_cd,
            "item_name": row.item_name,
            "qty": row.qty,  # Packing_Cs의 수량 사용
            "prod_date": row.prod_date,
            "insrt_dt": row.insrt_dt.strftime('%Y-%m-%d') if row.insrt_dt else None
        }
        for row in left_table_query
    ]

    # 모든 발주 데이터를 조회 (오른쪽 테이블)
    right_table_query = db.session.query(
        Purchase_Order.PO_NO.label("po_no"),
        Purchase_Order.PO_SEQ_NO.label("po_seq"),
        Purchase_Order.ITEM_CD.label("item_cd"),
        Item.ITEM_NM.label("item_name"),
        Purchase_Order.SL_CD.label("sl_cd"),
        Purchase_Order.BP_CD.label("bp_cd"),
        Purchase_Order.PO_QTY.label("po_qty"),
        Purchase_Order.OUT_QTY.label("out_qty"),
        Purchase_Order.IN_QTY.label("in_qty")
    ).join(
        Item, Purchase_Order.ITEM_CD == Item.ITEM_CD, isouter=True  # 품목 연결 (OUTER JOIN)
    ).all()

    # 결과 데이터 포맷 (오른쪽 테이블)
    right_table_data = [
        {
            "po_no": row.po_no,
            "po_seq": row.po_seq,
            "item_cd": row.item_cd,
            "item_name": row.item_name,
            "sl_cd": row.sl_cd,
            "bp_cd": row.bp_cd,
            "po_qty": row.po_qty,
            "out_qty": row.out_qty,
            "in_qty": row.in_qty
        }
        for row in right_table_query
    ]

    # 렌더링
    return render_template(
        'product/product_register_sterilizating_in.html',
        left_table_data=left_table_data,  # 왼쪽 테이블에 전달할 데이터
        right_table_data=right_table_data,  # 오른쪽 테이블에 전달할 데이터
        INSRT_DT_START=start_date.strftime('%Y-%m-%d'),
        INSRT_DT_END=end_date.strftime('%Y-%m-%d')
    )

# 멸균제품 입고등록 QR 체크 로직 함수
@bp.route('/get_sterilized_packing_data/', methods=['POST'])
def get_sterilized_packing_data():
    try:
        request_data = request.get_json()
        logging.info(f"Request Data: {request_data}")

        udi_qr = request_data.get('udi_qr')
        logging.info(f"Received UDI QR: {udi_qr}")

        if not udi_qr or len(udi_qr) != 47:
            logging.warning("Invalid QR Code Length or Missing QR Code")
            return jsonify({'status': 'error', 'message': 'QR 코드가 유효하지 않습니다. 47자리를 입력하세요.'}), 400

        # Packing_Cs 데이터 조회
        packing_cs_data = db.session.query(
            Packing_Cs.m_box_no,
            Packing_Cs.cs_model,
            Packing_Cs.cs_qty,
            Packing_Cs.cs_prod_date
        ).filter(Packing_Cs.cs_udi_qr == udi_qr).first()

        if not packing_cs_data:
            logging.warning(f"No data found in Packing_Cs for QR Code: {udi_qr}")
            return jsonify({'status': 'error', 'message': '해당 QR 코드에 대한 데이터를 찾을 수 없습니다.'}), 404

        logging.info(f"QR Code {udi_qr} fetched successfully.")

        return jsonify({
            'status': 'success',
            'packing_cs': {
                'm_box_no': packing_cs_data.m_box_no,
                'cs_model': packing_cs_data.cs_model,
                'cs_qty': int(packing_cs_data.cs_qty),
                'cs_prod_date': packing_cs_data.cs_prod_date,
                'po_no': request_data.get('po_no'),  # 발주 번호
                'po_seq_no': request_data.get('po_seq_no')  # 발주 SEQ
            }
        })

    except Exception as e:
        logging.error(f"Error in get_sterilized_packing_data: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

# 멸균 입고 데이터 등록 함수 (flow and doc)
@bp.route('/register_sterilized_packing/', methods=['POST'])
def register_sterilized_packing():
    try:
        data = request.json
        logging.info(f"Received data for sterilized packing registration: {data}")

        if not data or 'rows' not in data:
            return jsonify({"status": "error", "message": "No rows provided for processing"}), 400

        # 새로운 DOC_NO 생성
        doc_no = generate_doc_no()

        doc_seq = 10
        new_material_docs = []
        purchase_order_updates = {}  # PURCHASE_ORDER 업데이트를 위한 dict

        # 처리할 데이터 반복
        for row in data['rows']:
            m_box_no = row.get('m_box_no')
            po_no = row.get('po_no')  # 발주번호
            po_seq_no = row.get('po_seq_no')  # 발주 SEQ 번호
            cs_qty = row.get('cs_qty', 0)

            if not m_box_no or not po_no or po_seq_no is None:
                logging.warning(f"Missing m_box_no, po_no, or po_seq_no in the request row: {row}")
                continue

            # Barcode_Flow에서 m_box_no와 FROM_SL_CD='WO00061' 조건으로 조회
            barcodes = db.session.query(Barcode_Flow).filter_by(BOX_NUM=m_box_no, TO_SL_CD='WO00061').all()

            if not barcodes:
                logging.warning(f"No barcodes found for m_box_no: {m_box_no} with FROM_SL_CD='WO00061'")
                continue

            # BOM에서 상위 품목(PRNT_ITEM_CD) 조회
            for barcode_entry in barcodes:
                bom_item = db.session.query(Bom_Detail.PRNT_ITEM_CD).filter(
                    Bom_Detail.CHILD_ITEM_CD == barcode_entry.ITEM_CD,
                    Bom_Detail.VALID_TO_DT >= datetime.now(),  # 유효한 BOM 데이터만 선택
                    Bom_Detail.VALID_FROM_DT <= datetime.now()
                ).first()

                parent_item_cd = bom_item.PRNT_ITEM_CD if bom_item else barcode_entry.ITEM_CD
                logging.info(f"BOM parent item for ITEM_CD={barcode_entry.ITEM_CD}: {parent_item_cd}")

                # Barcode_Flow에 새 데이터 생성
                new_barcode_flow = Barcode_Flow(
                    barcode=barcode_entry.barcode,
                    ITEM_CD=parent_item_cd,  # BOM 상위 품목
                    WC_CD=None,
                    FROM_SL_CD='WO00061',  # 출발 창고 코드
                    TO_SL_CD='SF32',  # 입고 창고 코드
                    MOV_TYPE='T01',  # 입고 타입
                    CREDIT_DEBIT='C',
                    REPORT_TYPE='G',
                    BP_CD='O00061',  # 외주 업체 코드
                    BOX_NUM=m_box_no,
                    DOC_NO=doc_no,  # 생성된 DOC_NO 추가
                    DOC_SEQ=f"{doc_seq:02}",
                    PO_NO=po_no,  # 발주 번호 추가
                    PO_SEQ_NO=po_seq_no,  # 발주 SEQ 추가
                    INSRT_DT=datetime.now(),
                    INSRT_USR=g.user.USR_ID,
                    UPDT_USR=g.user.USR_ID
                )
                db.session.add(new_barcode_flow)

                # Material_Doc 데이터 생성
                material_doc = {
                    'DOC_NO': doc_no,
                    'DOC_SEQ': f"{doc_seq:02}",
                    'ITEM_CD': parent_item_cd,  # BOM 상위 품목
                    'QTY': cs_qty,  # 수량은 입력받은 cs_qty 사용
                    'CREDIT_DEBIT': 'C',
                    'MOV_TYPE': 'T01',
                    'FROM_SL_CD': 'WO00061',
                    'TO_SL_CD': 'SF32',
                    'REPORT_TYPE': 'G',
                    'BOX_NUM': m_box_no,
                    'BP_CD': 'O00061',
                    'PO_NO': po_no,  # 발주 번호 추가
                    'PO_SEQ_NO': po_seq_no,  # 발주 SEQ 추가
                    'INSRT_DT': datetime.now(),
                    'INSRT_USR': g.user.USR_ID,
                    'UPDT_DT': datetime.now(),
                    'UPDT_USR': g.user.USR_ID
                }
                new_material_docs.append(material_doc)
                doc_seq += 10

            # PURCHASE_ORDER 모델의 IN_QTY 업데이트를 위한 데이터 준비
            if (po_no, po_seq_no) in purchase_order_updates:
                purchase_order_updates[(po_no, po_seq_no)] += cs_qty
            else:
                purchase_order_updates[(po_no, po_seq_no)] = cs_qty

        # Material_Doc에 데이터 삽입
        if new_material_docs:
            db.session.bulk_insert_mappings(Material_Doc, new_material_docs)

        # PURCHASE_ORDER 모델의 IN_QTY 업데이트
        for (po_no, po_seq_no), in_qty_to_add in purchase_order_updates.items():
            purchase_order_query = db.session.query(Purchase_Order).filter_by(PO_NO=po_no, PO_SEQ_NO=po_seq_no).first()
            if not purchase_order_query:
                logging.warning(f"No purchase order found for PO_NO={po_no}, PO_SEQ_NO={po_seq_no}.")
                continue

            # IN_QTY 초기화 및 업데이트
            if purchase_order_query.IN_QTY is None:
                purchase_order_query.IN_QTY = 0
            purchase_order_query.IN_QTY += in_qty_to_add
            logging.info(f"Updated IN_QTY for PO_NO={po_no}, PO_SEQ_NO={po_seq_no} to {purchase_order_query.IN_QTY}.")

        # Barcode_Status 업데이트
        update_barcode_status_after_sterilizing_in(doc_no)

        # 변경사항 커밋
        db.session.commit()

        return jsonify({"status": "success", "message": f"멸균 외주 입고 등록 완료: {doc_no}"})

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error registering sterilized packing data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# 멸균 입고 후 상태 업데이트
def update_barcode_status_after_sterilizing_in(doc_no):
    try:
        barcodes = db.session.query(Barcode_Flow.barcode).filter(
            Barcode_Flow.DOC_NO == doc_no,
            Barcode_Flow.TO_SL_CD == 'SF32'  # 입고된 외주 창고 코드
        ).distinct().all()

        barcode_list = [barcode_tuple[0] for barcode_tuple in barcodes]

        if not barcode_list:
            logging.info(f"No barcodes found with DOC_NO={doc_no} and TO_SL_CD='SF32'.")
            return

        for barcode in barcode_list:
            status_record = db.session.query(Barcode_Status).filter(
                Barcode_Status.barcode == barcode
            ).first()

            if status_record:
                status_record.STATUS = 'S7'  # 입고 상태
                logging.info(f"Updated Barcode_Status for barcode={barcode} to STATUS='S7'.")
            else:
                new_status_record = Barcode_Status(
                    barcode=barcode,
                    STATUS='S7'
                )
                db.session.add(new_status_record)
                logging.info(f"Inserted new Barcode_Status for barcode={barcode} with STATUS='S7'.")

        db.session.commit()
        logging.info("Barcode_Status successfully updated to 'S7' for all relevant barcodes.")

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating Barcode_Status: {str(e)}")
        raise

# 박스 번호 기반 바코드 조회
@bp.route('/get_barcodes_by_sterilized_box/', methods=['POST'])
def get_barcodes_by_sterilized_box():
    try:
        data = request.json
        logging.info(f"Received request for barcodes by box: {data}")

        if not data or 'm_box_no' not in data:
            return jsonify({"status": "error", "message": "Missing 'm_box_no' field"}), 400

        box_num = data['m_box_no']

        barcodes = db.session.query(Barcode_Flow.barcode).filter_by(BOX_NUM=box_num).all()

        if not barcodes:
            return jsonify({"status": "error", "message": f"No barcodes found for m_box_no {box_num}"}), 404

        barcode_list = [b.barcode for b in barcodes]
        logging.info(f"Barcodes for m_box_no {box_num}: {barcode_list}")

        return jsonify({"status": "success", "barcodes": barcode_list})

    except Exception as e:
        logging.error(f"Error fetching barcodes by box: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# 멸균제품 입고 결과 조회 렌더링 (doc 기준)
@bp.route('/result_sterilizating_in/', methods=['GET', 'POST'])
def product_result_sterilizating_in():
    plant_code = request.form.get('plant_code', '').strip()
    from_sl_cd = request.form.get('from-sl-cd', 'SF40').strip()
    to_sl_cd = request.form.get('to-sl-cd', '').strip()

    # 오늘 기준 ±15일 기본 설정
    today = datetime.now()
    default_start_date = (today - timedelta(days=15)).strftime('%Y-%m-%d')
    default_end_date = (today + timedelta(days=15)).strftime('%Y-%m-%d')

    # 폼에서 날짜 값 가져오기
    start_date = request.form.get('start_date', default_start_date).strip()
    end_date = request.form.get('end_date', default_end_date).strip()

    # 날짜 변환
    start_date_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_date_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1, seconds=-1)

    # 기본 쿼리 작성
    query = (
        db.session.query(
            Material_Doc.DOC_NO,
            Material_Doc.DOC_SEQ,
            Material_Doc.ITEM_CD,
            Item.ITEM_NM,
            Material_Doc.BP_CD,
            Biz_Partner.bp_nm,
            Item.BASIC_UNIT,
            Material_Doc.PO_NO,
            Material_Doc.PO_SEQ_NO,
            Material_Doc.TO_SL_CD,
            Material_Doc.QTY,
            Material_Doc.BOX_NUM,
            Material_Doc.INSRT_DT
        )
        .join(Item, Material_Doc.ITEM_CD == Item.ITEM_CD, isouter=True)
        .join(Biz_Partner, Material_Doc.BP_CD == Biz_Partner.bp_cd, isouter=True)
    )
    query = query.filter(Material_Doc.TO_SL_CD == 'SF32')

    # 검색 조건 적용
    if plant_code:
        query = query.filter(Material_Doc.PLANT_CD == plant_code)
    if to_sl_cd:
        query = query.filter(Material_Doc.TO_SL_CD == to_sl_cd)
    if start_date_dt and end_date_dt:
        query = query.filter(
            cast(Material_Doc.INSRT_DT, Date) >= start_date_dt.date(),
            cast(Material_Doc.INSRT_DT, Date) <= end_date_dt.date()
        )

    # 결과 조회
    orders_with_hdr = query.order_by(Material_Doc.DOC_NO, Material_Doc.DOC_SEQ).all()

    # 템플릿 렌더링
    return render_template(
        'product/product_result_sterilizating_in.html',
        orders_with_hdr=orders_with_hdr,
        INSRT_DT_START=start_date,
        INSRT_DT_END=end_date,
        form_submitted=True
    )
