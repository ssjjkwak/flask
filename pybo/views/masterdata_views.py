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
    # 1. 필요한 데이터 생성
    today = datetime.today().strftime('%Y-%m-%d')
    plants = db.session.query(Plant).all()

    # 모품목(PRNT_ITEM_CD)
    top_level_items = db.session.query(Bom_Detail.PRNT_ITEM_CD).distinct().all()

    selected_parent_item_cd = request.form.get('parent_item_cd') if request.method == 'POST' else None
    selected_plant_code = request.form.get('plant_code') if request.method == 'POST' else None
    start_date = request.form.get('start_date') if request.method == 'POST' else today

    # 선택된 조건을 기준으로 BOM 데이터를 필터링
    bom_items = []
    if selected_parent_item_cd and start_date:
        # 선택된 최상위 품목과 기준일을 기반으로 BOM 데이터 필터링
        def get_bom_hierarchy(parent_item_cd):
            items = db.session.query(Bom_Detail).filter(
                Bom_Detail.PRNT_ITEM_CD == parent_item_cd,
                Bom_Detail.VALID_FROM_DT <= start_date,
                Bom_Detail.VALID_TO_DT >= start_date
            ).all()
            bom_items.extend(items)
            for item in items:
                get_bom_hierarchy(item.CHILD_ITEM_CD)

        # 선택된 최상위 품목에 연결된 전체 BOM 트리를 조회
        get_bom_hierarchy(selected_parent_item_cd)

    # 4. ITEM 테이블에서 자품목 정보 (CHILD_ITEM_CD에 해당하는 정보)
    item_details = {item.ITEM_CD: item for item in db.session.query(Item).all()}

    # 5. BOM 데이터를 계층 구조로 변환
    def build_bom_tree(bom_items, item_details):
        tree = []
        item_map = {}

        for item in bom_items:
            # Item 테이블에서 자품목과 매칭되는 항목을 가져와서 SPEC과 ITEM_ACCT 추가
            child_item = item_details.get(item.CHILD_ITEM_CD)

            bom_item = {
                'seq': item.CHILD_ITEM_SEQ,
                'prnt_item_cd': item.PRNT_ITEM_CD,  # 모품목 코드
                'prnt_item_nm': item.PRNT_ITEM_CD,  # 모품목명
                'child_item_cd': item.CHILD_ITEM_CD,  # 자품목 코드
                'item_nm': child_item.ITEM_NM if child_item else None,
                'spec': child_item.SPEC if child_item else None,  # 규격
                'item_acct': child_item.ITEM_ACCT if child_item else None,  # 품목계정
                'child_item_qty': item.CHILD_ITEM_QTY,  # 자품목 수량
                'child_item_unit': item.CHILD_ITEM_UNIT,  # 자품목 단위
                'prnt_item_qty': item.PRNT_ITEM_QTY,
                'prnt_item_unit': item.PRNT_ITEM_UNIT,
                'loss_rate': item.LOSS_RATE,  # 손실율
                'valid_from_dt': item.VALID_FROM_DT,  # 유효기간 시작
                'valid_to_dt': item.VALID_TO_DT,  # 유효기간 종료
                'level': 1  # 기본적으로 1단계로 시작
            }

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
        top_level_items = set(item_map.keys()) - set([item.CHILD_ITEM_CD for item in bom_items])
        for parent_id in top_level_items:
            add_children(parent_id, 1)

        return tree

    # 6. 계층 구조로 변환된 BOM 데이터.
    bom_tree_structure = build_bom_tree(bom_items, item_details)

    # 7. 템플릿에 최상위 모품목 목록과 선택된 최상위 품목을 전달
    return render_template(
        'masterdata/bom.html',
        bom_tree_structure=bom_tree_structure,
        parent_item_cd=selected_parent_item_cd,
        top_level_items=top_level_items,  # 최상위 품목 목록을 템플릿으로 전달
        plants=plants,  # 공장 목록 전달
        selected_plant_code=selected_plant_code,
        start_date=start_date
    )


#거래처정보조회
@bp.route('/vendor/', methods=['GET', 'POST'])
def vendor():

    return render_template('masterdata/vendor.html', show_navigation_bar=True)