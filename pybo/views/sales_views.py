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
    Barcode_Flow, Production_Results, kst_now, Packing_Hdr, Packing_Dtl, Sales_Order, Biz_Partner, Packing_Cs
from collections import defaultdict

bp = Blueprint('sales', __name__, url_prefix='/sales')


# 출하등록 렌더링
@bp.route('/sales_order/', methods=['GET', 'POST'])
def sales_order():
    start_date = request.form.get('start_date', (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')).strip()
    end_date = request.form.get('end_date', (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d')).strip()
    bp_cd = request.form.get('to-sl-cd', '').strip()  # 거래처 코드
    selected_bp_cd = request.form.get('to-sl-cd', '').strip()

    # 날짜 변환
    start_date_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_date_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1, seconds=-1)

    # 거래처 목록 가져오기 (bp_cd, bp_nm)
    biz_partners = db.session.query(Biz_Partner.bp_cd, Biz_Partner.bp_nm).all()

    # Packing_Cs와 Barcode_Flow를 JOIN하여 데이터 조회 (왼쪽 테이블)
    left_table_query = db.session.query(
        Packing_Cs.m_box_no.label("box_num"),  # Packing_Cs의 박스 번호
        Barcode_Flow.ITEM_CD.label("item_cd"),  # 품목 코드
        Item.ITEM_NM.label("item_name"),  # 품목명
        Packing_Cs.cs_qty.label("qty"),  # Packing_Cs의 수량
        Packing_Cs.cs_prod_date.label("prod_date"),  # 포장일자
        Barcode_Flow.INSRT_DT.label("insrt_dt")  # 삽입일자
    ).join(
        Barcode_Flow, Packing_Cs.m_box_no == Barcode_Flow.BOX_NUM  # Packing_Cs와 Barcode_Flow JOIN
    ).join(
        Item, Barcode_Flow.ITEM_CD == Item.ITEM_CD  # 품목 연결
    ).filter(
        Barcode_Flow.TO_SL_CD == 'SF50',  # TO_SL_CD가 'SF50'인 데이터만 필터링
        Barcode_Flow.INSRT_DT.between(start_date_dt, end_date_dt)  # 삽입일자 필터링
    ).distinct(
        Packing_Cs.m_box_no  # DISTINCT 기준 컬럼 설정
    ).all()

    # Sales_Order와 Item, Biz_Partner를 조인하여 오른쪽 테이블 데이터 조회
    right_table_query = db.session.query(
        Sales_Order.SO_NO.label("so_no"),  # 수주번호
        Sales_Order.SO_SEQ.label("so_seq"),  # 수주 SEQ
        Sales_Order.ITEM_CD.label("item_cd"),  # 품목 코드
        Item.ITEM_NM.label("item_name"),  # 품목명
        Sales_Order.SL_CD.label("sl_cd"),  # 창고 코드
        Sales_Order.SO_QTY.label("so_qty"),  # 수주 수량
        Sales_Order.DLVY_QTY.label("dlvy_qty"),  # 출하 수량
        Biz_Partner.bp_cd.label("bp_cd"),  # 거래처 코드
        Biz_Partner.bp_nm.label("bp_nm")  # 거래처 이름
    ).join(
        Item, Sales_Order.ITEM_CD == Item.ITEM_CD, isouter=True  # Item과 OUTER JOIN
    ).join(
        Biz_Partner, Sales_Order.BP_CD == Biz_Partner.bp_cd, isouter=True  # Biz_Partner와 OUTER JOIN
    ).filter(
        Sales_Order.REQ_DLVY_DT.between(start_date_dt, end_date_dt)  # 수주일자 필터링
    )

    # 거래처 필터 추가
    if bp_cd:
        right_table_query = right_table_query.filter(Sales_Order.BP_CD == bp_cd)

    right_table_query = right_table_query.all()

    # 결과 데이터 포맷
    left_table_data = [
        {
            "box_num": row.box_num,
            "item_cd": row.item_cd,
            "item_name": row.item_name,
            "qty": row.qty,
            "prod_date": row.prod_date,
            "insrt_dt": row.insrt_dt.strftime('%Y-%m-%d') if row.insrt_dt else None
        }
        for row in left_table_query
    ]

    right_table_data = [
        {
            "so_no": row.so_no,
            "so_seq": row.so_seq,
            "item_cd": row.item_cd,
            "item_name": row.item_name,
            "sl_cd": row.sl_cd,
            "so_qty": row.so_qty,
            "dlvy_qty": row.dlvy_qty,
            "bp_cd": row.bp_cd,
            "bp_nm": row.bp_nm
        }
        for row in right_table_query
    ]

    # 렌더링
    return render_template(
        'sales/sales_order.html',
        left_table_data=left_table_data,  # 왼쪽 테이블 데이터
        right_table_data=right_table_data,  # 오른쪽 테이블 데이터
        biz_partners=biz_partners,  # 거래처 목록
        INSRT_DT_START=start_date,
        INSRT_DT_END=end_date,
        selected_bp_cd=selected_bp_cd
    )








@bp.route('/supply_details/', methods=['GET'])
def supply_details():

    return render_template('sales/supply_details.html',  show_navigation_bar=True)