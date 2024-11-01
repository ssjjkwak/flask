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
    Barcode_Flow, Production_Results, kst_now, Packing_Hdr, Packing_Dtl, Item_Group, Item_Alpha, Bom_Header, Bom_Detail, Biz_Partner
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bp = Blueprint('masterdata', __name__, url_prefix='/masterdata')

# 품목정보조회
@bp.route('/item/', methods=['GET', 'POST'])
def item():
    form_submitted = False
    PLANT_CD = ''
    ITEM_CD = ''
    ITEM_NM = ''
    ITEM_GROUP_CD = ''
    UDI_CODE = ''
    ITEM_ACCT = ''
    ALPHA_CODE = ''
    BASIC_UNIT = ''
    PRODUCT_NM = ''
    MODEL_NM = ''
    GTIN_CODE1 = ''
    PAC_QTY1 = ''
    MINOR_CATEGORY_NM = ''
    GRADE = ''
    ITEM_PERMIT_NO = ''
    MEDICAL_CARE_BENEFIT_FLAG = ''


    # 모든 공장 목록, 품목그룹 목록, 알파코드 목록을 조회하여 화면에 표시
    plants = db.session.query(Plant).all()
    item_groups = db.session.query(Item_Group).all()
    alpha_codes = db.session.query(Item_Alpha).all()

    # 아이템과 관련된 기본 쿼리
    items_query = db.session.query(Item).outerjoin(Item_Group, Item.ITEM_GROUP_CD == Item_Group.ITEM_GROUP_CD)

    # Item_Master와 Item의 ALPHA_CODE 조인을 추가하여 ALPHA_CODE가 NULL인 데이터도 포함
    items_query = items_query.outerjoin(Item_Alpha, Item.ALPHA_CODE == Item_Alpha.ALPHA_CODE)

    if request.method == 'POST':
        form_submitted = True
        # 입력된 조회 조건을 가져옴
        PLANT_CD = request.form.get('plant_code', '')
        ITEM_CD = request.form.get('item_cd', '')
        ITEM_NM = request.form.get('item_nm', '')
        ITEM_GROUP_CD = request.form.get('item_group_cd', '')
        UDI_CODE = request.form.get('udi_code', '')
        ITEM_ACCT = request.form.get('item_acct', '')
        ALPHA_CODE = request.form.get('alpha_code', '')
        BASIC_UNIT = request.form.get('basic_unit', '')
        PRODUCT_NM = request.form.get('product_nm', '')
        MODEL_NM = request.form.get('model_nm', '')
        GTIN_CODE1 = request.form.get('gtin_code1', '')
        PAC_QTY1 = request.form.get('pac_qty1', '')
        MINOR_CATEGORY_NM = request.form.get('minor_category_nm', '')
        GRADE = request.form.get('grade', '')
        ITEM_PERMIT_NO = request.form.get('item_permit_no', '')
        MEDICAL_CARE_BENEFIT_FLAG = request.form.get('medical_care_benefit_flag', '')

        # 필터링 조건을 적용
        if PLANT_CD:
            items_query = items_query.filter(Item.PLANT_CD == PLANT_CD)
        if ITEM_CD:
            items_query = items_query.filter(Item.ITEM_CD.like(f'%{ITEM_CD}%'))
        if ITEM_NM:
            items_query = items_query.filter(Item.ITEM_NM.like(f'%{ITEM_NM}%'))
        if ITEM_GROUP_CD:
            items_query = items_query.filter(Item.ITEM_GROUP_CD == ITEM_GROUP_CD)
        if UDI_CODE:
            items_query = items_query.filter(Item.UDI_CODE.like(f'%{UDI_CODE}%'))
        if ITEM_ACCT:
            items_query = items_query.filter(Item.ITEM_ACCT == ITEM_ACCT)
        if ALPHA_CODE:  # 알파코드 필터링 추가 (ALPHA_CODE가 선택된 경우만 필터링 적용)
            items_query = items_query.filter(Item_Alpha.ALPHA_CODE == ALPHA_CODE)

        # BASIC_UNIT 필터링 추가, 없으면 모든 데이터 포함
        if BASIC_UNIT:
            items_query = items_query.filter(Item.BASIC_UNIT == BASIC_UNIT)

    # 조회 결과 가져오기
    items = items_query.all()

    return render_template('masterdata/item.html',
                           plants=plants,
                           items=items,
                           item_groups=item_groups,
                           alpha_codes=alpha_codes,
                           PLANT_CD=PLANT_CD,
                           ITEM_CD=ITEM_CD,
                           ITEM_NM=ITEM_NM,
                           ITEM_GROUP_CD=ITEM_GROUP_CD,
                           UDI_CODE=UDI_CODE,
                           ITEM_ACCT=ITEM_ACCT,
                           ALPHA_CODE=ALPHA_CODE,
                           BASIC_UNIT=BASIC_UNIT,
                           PRODUCT_NM=PRODUCT_NM,
                           MODEL_NM=MODEL_NM,
                           GTIN_CODE1=GTIN_CODE1,
                           PAC_QTY1=PAC_QTY1,
                           MINOR_CATEGORY_NM=MINOR_CATEGORY_NM,
                           GRADE=GRADE,
                           ITEM_PERMIT_NO=ITEM_PERMIT_NO,
                           MEDICAL_CARE_BENEFIT_FLAG=MEDICAL_CARE_BENEFIT_FLAG,
                           form_submitted=form_submitted)


@bp.route('/item/get_item', methods=['POST'])
def get_item():
    data = request.get_json()  # 클라이언트로부터 받은 JSON 데이터
    item_cd = data.get('item_cd')  # item_cd 값 추출
    logging.info(f"Received item_cd: {item_cd}")

    item = db.session.query(Item).filter(Item.ITEM_CD == item_cd).first()

    if item:
        logging.info(f"Found item: {item.ITEM_CD}")
        return jsonify({
            'ITEM_CD': item.ITEM_CD,
            'ITEM_NM': item.ITEM_NM or '',  # 기본값 설정
            'SPEC': item.SPEC or '',  # 기본값 설정
            'ITEM_ACCT': item.ITEM_ACCT or '',  # 기본값 설정
            'BASIC_UNIT': item.BASIC_UNIT or '',  # 기본값 설정
            'ALPHA_CODE': item.ALPHA_CODE or '',
            'UDI_CODE': item.UDI_CODE or '',
            'PRODUCT_NM': item.PRODUCT_NM or '',
            'MODEL_NM': item.MODEL_NM or '',
            'GTIN_CODE1': item.GTIN_CODE1 or '',
            'PAC_QTY1': item.PAC_QTY1 or '',
            'MINOR_CATEGORY_NM': item.MINOR_CATEGORY_NM or '',
            'GRADE': item.GRADE or '',
            'ITEM_PERMIT_NO': item.ITEM_PERMIT_NO or '',
            'MEDICAL_CARE_BENEFIT_FLAG': item.MEDICAL_CARE_BENEFIT_FLAG or ''
        })
    else:
        logging.info(f"Item not found for ITEM_CD: {item_cd}")
        return jsonify({'error': 'Item not found'}), 404


@bp.route('/item/update_item', methods=['POST'])
def update_item():
    item_cd = request.form.get('modal_item_cd')
    item_nm = request.form.get('modal_item_nm')
    spec = request.form.get('modal_spec')
    item_acct = request.form.get('modal_item_acct')
    basic_unit = request.form.get('modal_basic_unit')
    alpha_code = request.form.get('modal_alpha_code')
    udi_code = request.form.get('modal_udi_code')
    gtin_code1 = request.form.get('modal_gtin_code1')
    pac_qty1 = request.form.get('modal_pac_qty1')
    minor_category_nm = request.form.get('modal_minor_category_nm')
    grade = request.form.get('modal_grade')
    product_nm = request.form.get('modal_product_nm')
    item_permit_no = request.form.get('modal_item_permit_no')
    model_nm = request.form.get('modal_model_nm')
    medical_care_benefit_flag = request.form.get('modal_medical_care_benefit_flag')


    # 해당 ITEM_CD로 DB에서 아이템을 찾음
    item = db.session.query(Item).filter(Item.ITEM_CD == item_cd).first()

    if item:
        # 데이터 업데이트
        item.ITEM_NM = item_nm
        item.SPEC = spec
        item.ITEM_ACCT = item_acct
        item.BASIC_UNIT = basic_unit
        item.ALPHA_CODE = alpha_code
        item.UDI_CODE = udi_code
        item.PRODUCT_NM = product_nm
        item.MODEL_NM = model_nm
        item.GTIN_CODE1 = gtin_code1
        item.PAC_QTY1 = pac_qty1
        item.MINOR_CATEGORY_NM = minor_category_nm
        item.GRADE = grade
        item.ITEM_PERMIT_NO = item_permit_no
        item.MEDICAL_CARE_BENEFIT_FLAG = medical_care_benefit_flag

        # DB에 커밋
        db.session.commit()
        return jsonify({'success': True})

    return jsonify({'error': 'Item not found'}), 404


# BOM정보조회
@bp.route('/bom/', methods=['GET', 'POST'])
def bom():
    # 1. 필요한 데이터 생성
    today = datetime.today().strftime('%Y-%m-%d')
    plants = db.session.query(Plant).all()
    top_level_items = db.session.query(Bom_Detail.PRNT_ITEM_CD).distinct().all()

    form_submitted = False  # 조회 버튼이 눌렸는지 여부를 확인하는 변수
    gtin_code = None  # 유통코드를 저장할 변수

    # 선택된 값 가져오기
    selected_parent_item_cd = request.form.get('parent_item_cd') if request.method == 'POST' else None
    selected_plant_code = request.form.get('plant_code') if request.method == 'POST' else None
    start_date = request.form.get('start_date') if request.method == 'POST' else today

    # 선택된 모품목의 유통코드 조회
    if selected_parent_item_cd:
        # 유통코드는 최상위 품목에서 가져오므로 해당 품목의 유통코드를 조회
        parent_item = db.session.query(Item).filter(Item.ITEM_CD == selected_parent_item_cd).first()
        gtin_code = parent_item.GTIN_CODE1 if parent_item else None

    # 조회 버튼을 눌렀을 때만 데이터를 가져오게 처리
    bom_items = []
    if request.method == 'POST':
        form_submitted = True
        if selected_parent_item_cd and start_date:
            # 선택된 최상위 품목과 기준일을 기반으로 BOM 데이터 필터링
            def get_bom_hierarchy(parent_item_cd):
                query = db.session.query(Bom_Detail, Item).join(
                    Item, Bom_Detail.CHILD_ITEM_CD == Item.ITEM_CD
                ).filter(
                    Bom_Detail.PRNT_ITEM_CD == parent_item_cd,
                    Bom_Detail.VALID_FROM_DT <= start_date,
                    Bom_Detail.VALID_TO_DT >= start_date
                )
                if selected_plant_code:
                    query = query.filter(Bom_Detail.PRNT_PLANT_CD == selected_plant_code)
                items = query.all()
                bom_items.extend(items)
                for item in items:
                    get_bom_hierarchy(item[0].CHILD_ITEM_CD)  # 아이템의 첫 번째 요소는 Bom_Detail

            # 선택된 최상위 품목에 연결된 전체 BOM 트리를 조회
            get_bom_hierarchy(selected_parent_item_cd)

    # BOM 데이터를 계층 구조로 변환
    def build_bom_tree(bom_items):
        tree = []
        item_map = {}

        for bom_detail, item in bom_items:
            # Item 테이블에서 추가된 정보를 가져와서 ALPHA_CODE, UDI_CODE, GTIN_CODE1 추가
            bom_item = {
                'seq': bom_detail.CHILD_ITEM_SEQ,
                'prnt_item_cd': bom_detail.PRNT_ITEM_CD,
                'child_item_cd': bom_detail.CHILD_ITEM_CD,
                'item_nm': item.ITEM_NM if item else None,
                'spec': item.SPEC if item else None,
                'item_acct': item.ITEM_ACCT if item else None,
                'child_item_qty': bom_detail.CHILD_ITEM_QTY,
                'child_item_unit': bom_detail.CHILD_ITEM_UNIT,
                'prnt_item_qty': bom_detail.PRNT_ITEM_QTY,
                'prnt_item_unit': bom_detail.PRNT_ITEM_UNIT,
                'loss_rate': bom_detail.LOSS_RATE,
                'valid_from_dt': bom_detail.VALID_FROM_DT,
                'valid_to_dt': bom_detail.VALID_TO_DT,
                'alpha_code': item.ALPHA_CODE if item else None,  # ALPHA_CODE 추가
                'udi_code': item.UDI_CODE if item else None,  # UDI_CODE 추가
                'gtin_code1': item.GTIN_CODE1 if item else None,  # GTIN_CODE1 추가
                'level': 1
            }

            parent_id = bom_detail.PRNT_ITEM_CD
            if parent_id not in item_map:
                item_map[parent_id] = []
            item_map[parent_id].append(bom_item)

        def add_children(item_cd, level):
            if item_cd in item_map:
                for child in item_map[item_cd]:
                    child['level'] = level
                    tree.append(child)
                    add_children(child['child_item_cd'], level + 1)

        top_level_items = set(item_map.keys()) - set([bom_detail.CHILD_ITEM_CD for bom_detail, _ in bom_items])
        for parent_id in top_level_items:
            add_children(parent_id, 1)

        return tree

    bom_tree_structure = build_bom_tree(bom_items) if bom_items else []

    return render_template(
        'masterdata/bom.html',
        bom_tree_structure=bom_tree_structure,
        parent_item_cd=selected_parent_item_cd,
        top_level_items=top_level_items,
        plants=plants,
        selected_plant_code=selected_plant_code,
        start_date=start_date,
        form_submitted=form_submitted,
        gtin_code=gtin_code
    )




#거래처정보조회
# 거래처 조회 및 필터링
@bp.route('/vendor/', methods=['GET', 'POST'])
def vendor():
    form_submitted = False
    bp_cd = ''
    bp_nm = ''

    # 기본 쿼리 생성 (거래처 정보를 조회)
    vendors_query = db.session.query(Biz_Partner)

    if request.method == 'POST':
        form_submitted = True
        bp_cd = request.form.get('bp_cd', '')
        bp_nm = request.form.get('bp_nm', '')

        # 필터링 조건 적용
        if bp_cd:
            vendors_query = vendors_query.filter(Biz_Partner.bp_cd.like(f'%{bp_cd}%'))
        if bp_nm:
            vendors_query = vendors_query.filter(Biz_Partner.bp_nm.like(f'%{bp_nm}%'))

    # 조회 결과 가져오기
    vendors = vendors_query.all()

    return render_template('masterdata/vendor.html',
                           vendors=vendors,
                           form_submitted=form_submitted,
                           bp_cd=bp_cd,
                           bp_nm=bp_nm)

# 특정 거래처 정보 조회
@bp.route('/vendor/get_vendor', methods=['POST'])
def get_vendor():
    data = request.get_json()  # 클라이언트로부터 받은 JSON 데이터
    bp_cd = data.get('bp_cd')  # 거래처 코드 (bp_cd) 값 추출

    # 해당 거래처 조회
    vendor = db.session.query(Biz_Partner).filter(Biz_Partner.bp_cd == bp_cd).first()

    if vendor:
        return jsonify({
            'bp_cd': vendor.bp_cd,
            'bp_nm': vendor.bp_nm or '',
            'bp_rgst_no': vendor.bp_rgst_no or '',
            'nids_cd': vendor.nids_cd or '',
            'repre_nm': vendor.repre_nm or '',
            'addr1': vendor.addr1 or '',
            'addr2': vendor.addr2 or '',
            'usage_flag': vendor.usage_flag or ''
        })
    else:
        return jsonify({'error': 'Vendor not found'}), 404

# 거래처 정보 업데이트
@bp.route('/vendor/update_vendor', methods=['POST'])
def update_vendor():
    # 받아온 form 데이터를 처리
    bp_cd = request.form.get('bp_cd')
    bp_nm = request.form.get('bp_nm', '')  # 빈 문자열 기본값
    bp_rgst_no = request.form.get('bp_rgst_no', '')  # 빈 문자열 기본값
    nids_cd = request.form.get('nids_cd', '')  # 빈 문자열 기본값
    repre_nm = request.form.get('repre_nm', '')  # 빈 문자열 기본값
    addr1 = request.form.get('addr1', '')  # 빈 문자열 기본값
    addr2 = request.form.get('addr2', '')  # 빈 문자열 기본값
    usage_flag = request.form.get('usage_flag', '')  # 빈 문자열 기본값

    # 해당 거래처코드(bp_cd)로 DB에서 거래처 정보 찾기
    vendor = db.session.query(Biz_Partner).filter_by(bp_cd=bp_cd).first()

    if vendor:
        # 값이 빈 문자열이면 None으로 변환해서 처리
        vendor.bp_nm = bp_nm if bp_nm else None
        vendor.bp_rgst_no = bp_rgst_no if bp_rgst_no else None
        vendor.nids_cd = nids_cd if nids_cd else None
        vendor.repre_nm = repre_nm if repre_nm else None
        vendor.addr1 = addr1 if addr1 else None
        vendor.addr2 = addr2 if addr2 else None
        vendor.usage_flag = usage_flag if usage_flag else None

        # 변경 사항을 DB에 반영
        db.session.commit()
        return jsonify(success=True)
    else:
        return jsonify(success=False, error='Vendor not found')



