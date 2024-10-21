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
    Production_Barcode_Assign, Production_Results, kst_now, Packing_Hdr, Packing_Dtl, Item_Group, Item_Master, Bom_Header, Bom_Detail
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bp = Blueprint('masterdata', __name__, url_prefix='/masterdata')

# 품목정보조회
@bp.route('/item/', methods=['GET', 'POST'])
def item():
    form_submitted = False
    PLANT_CD = ''
    ITEM_CD = ''
    ITEM_GROUP_CD = ''
    UDI_CODE = ''
    ITEM_ACCT = ''
    ALPHA_CODE = ''
    BASIC_UNIT = ''

    # 모든 공장 목록, 품목그룹 목록, 알파코드 목록을 조회하여 화면에 표시
    plants = db.session.query(Plant).all()
    item_groups = db.session.query(Item_Group).all()
    alpha_codes = db.session.query(Item_Master).all()

    # 아이템과 관련된 기본 쿼리
    items_query = db.session.query(Item).outerjoin(Item_Group, Item.ITEM_GROUP_CD == Item_Group.ITEM_GROUP_CD)

    # Item_Master와 Item의 ALPHA_CODE 조인을 추가하여 ALPHA_CODE가 NULL인 데이터도 포함
    items_query = items_query.outerjoin(Item_Master, Item.ALPHA_CODE == Item_Master.ALPHA_CODE)

    if request.method == 'POST':
        form_submitted = True
        # 입력된 조회 조건을 가져옴
        PLANT_CD = request.form.get('plant_code', '')
        ITEM_CD = request.form.get('item_cd', '')
        ITEM_GROUP_CD = request.form.get('item_group_cd', '')
        UDI_CODE = request.form.get('udi_code', '')
        ITEM_ACCT = request.form.get('item_acct', '')
        ALPHA_CODE = request.form.get('alpha_code', '')
        BASIC_UNIT = request.form.get('basic_unit', '')  # BASIC_UNIT 추가

        # 필터링 조건을 적용
        if PLANT_CD:
            items_query = items_query.filter(Item.PLANT_CD == PLANT_CD)
        if ITEM_CD:
            items_query = items_query.filter(Item.ITEM_CD.like(f'%{ITEM_CD}%'))
        if ITEM_GROUP_CD:
            items_query = items_query.filter(Item.ITEM_GROUP_CD == ITEM_GROUP_CD)
        if UDI_CODE:
            items_query = items_query.filter(Item.UDI_CODE.like(f'%{UDI_CODE}%'))
        if ITEM_ACCT:
            items_query = items_query.filter(Item.ITEM_ACCT == ITEM_ACCT)
        if ALPHA_CODE:  # 알파코드 필터링 추가 (ALPHA_CODE가 선택된 경우만 필터링 적용)
            items_query = items_query.filter(Item_Master.ALPHA_CODE == ALPHA_CODE)

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
                           ITEM_GROUP_CD=ITEM_GROUP_CD,
                           UDI_CODE=UDI_CODE,
                           ITEM_ACCT=ITEM_ACCT,
                           ALPHA_CODE=ALPHA_CODE,
                           BASIC_UNIT=BASIC_UNIT,  # BASIC_UNIT 전달
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
            'UDI_CODE': item.UDI_CODE or ''
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

        # DB에 커밋
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Item not found'}), 404


# BOM정보조회
# 데이터 조회를 위한 라우트 함수
@bp.route('/bom/', methods=['GET', 'POST'])
def bom():
    # 1. BOM 데이터를 데이터베이스에서 가져옵니다.
    bom_items = db.session.query(Bom_Detail).all()

    # 2. BOM 데이터를 계층 구조로 변환 (이 부분은 이미 작성된 함수 로직을 사용)
    def build_bom_tree(bom_items):
        tree = []
        item_map = {}

        # 각 자품목을 부모 품목을 기준으로 분류
        for item in bom_items:
            # 항목을 dict로 변환
            bom_item = {
                'seq': item.CHILD_ITEM_SEQ,
                'child_item_cd': item.CHILD_ITEM_CD,
                'child_item_nm': item.CHILD_ITEM_CD,  # 자품목명 필드 추가
                'spec': item.CHILD_ITEM_UNIT,  # 규격 필드 추가
                'item_acct': item.PRNT_ITEM_UNIT,  # 품목계정 필드 추가
                'child_item_qty': item.CHILD_ITEM_QTY,
                'child_item_unit': item.CHILD_ITEM_UNIT,
                'loss_rate': item.LOSS_RATE,
                'valid_from_dt': item.VALID_FROM_DT,
                'valid_to_dt': item.VALID_TO_DT,
                'level': 1  # 기본적으로 1단계로 시작
            }

            # 부모 아이템을 기준으로 아이템들을 분류
            parent_id = item.PRNT_ITEM_CD
            if parent_id not in item_map:
                item_map[parent_id] = []
            item_map[parent_id].append(bom_item)

        # 계층 트리 빌드
        def add_children(item_cd, level):
            if item_cd in item_map:
                for child in item_map[item_cd]:
                    child['level'] = level
                    tree.append(child)
                    add_children(child['child_item_cd'], level + 1)

        # 최상위 부모들을 시작점으로 트리 구조 생성
        # 최상위 부모란 다른 항목의 자품목이 아닌 항목들을 의미
        top_level_items = set(item_map.keys()) - set([item.CHILD_ITEM_CD for item in bom_items])

        for parent_id in top_level_items:
            add_children(parent_id, 1)

        return tree

    # 3. 계층 구조로 변환된 BOM 데이터를 가져옵니다.
    bom_tree_structure = build_bom_tree(bom_items)

    # 4. 데이터를 템플릿으로 전달하여 렌더링
    return render_template('masterdata/bom.html', bom_tree_structure=bom_tree_structure)





#거래처정보조회
@bp.route('/vendor/', methods=['GET', 'POST'])
def vendor():

    return render_template('masterdata/vendor.html', show_navigation_bar=True)