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
    Barcode_Flow, Production_Results, kst_now, Packing_Hdr, Packing_Dtl, Sales_Order, Biz_Partner, Packing_Cs, Material_Doc
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

    # TO_SL_CD가 SF60인 박스 번호 가져오기
    excluded_boxes = db.session.query(Barcode_Flow.BOX_NUM).filter(
        Barcode_Flow.TO_SL_CD == 'SF60'
    ).distinct().subquery()

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
        Barcode_Flow.INSRT_DT.between(start_date_dt, end_date_dt),  # 삽입일자 필터링
        ~Packing_Cs.m_box_no.in_(excluded_boxes)  # TO_SL_CD가 SF60인 박스 제외
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

    right_table_bp_cd = right_table_query[0].bp_cd if right_table_query else ""
    right_table_bp_nm = right_table_query[0].bp_nm if right_table_query else ""

    # 결과 데이터 포맷
    seen_boxes = set()  # 이미 처리된 박스 번호를 저장
    left_table_data = []
    for row in left_table_query:
        if row.box_num not in seen_boxes:
            seen_boxes.add(row.box_num)
            left_table_data.append({
                "box_num": row.box_num,
                "item_cd": row.item_cd,
                "item_name": row.item_name,
                "qty": row.qty,
                "prod_date": row.prod_date,
                "insrt_dt": row.insrt_dt.strftime('%Y-%m-%d') if row.insrt_dt else None
            })

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
        selected_bp_cd=selected_bp_cd,
        right_table_bp_cd=right_table_bp_cd,  # 오른쪽 테이블의 거래처 코드
        right_table_bp_nm=right_table_bp_nm  # 오른쪽 테이블의 거래처 이름
    )

# doc 번호 생성
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

# 출하 모달에서 박스 스캔할 때, 박스번호에 대한 검증 로직
@bp.route('/sales_detail/', methods=['POST'])
def sales_detail():
    try:
        request_data = request.get_json()
        logging.info(f"요청 데이터: {request_data}")

        udi_qr = request_data.get('udi_qr')
        logging.info(f"QR 코드: {udi_qr}")

        if not udi_qr or len(udi_qr) != 47:
            logging.warning("잘못된 QR 코드 입력")
            return jsonify({'status': 'error', 'message': 'QR 코드가 유효하지 않습니다. 47자리를 입력하세요.'}), 400

        # Packing_Cs에서 데이터 조회
        logging.info("Packing_Cs 조회 시작")
        packing_data = db.session.query(
            Packing_Cs.m_box_no,
            Packing_Cs.cs_qty
        ).filter(Packing_Cs.cs_udi_qr == udi_qr).first()

        if not packing_data:
            logging.warning(f"Packing_Cs에서 데이터 없음. QR 코드: {udi_qr}")
            return jsonify({'status': 'error', 'message': 'Packing_Cs에서 해당 QR 코드를 찾을 수 없습니다.'}), 404

        BOX_NUM = packing_data.m_box_no
        cs_qty = packing_data.cs_qty
        logging.info(f"Packing_Cs 데이터: 박스번호={BOX_NUM}, 수량={cs_qty}")

        # Barcode_Flow에서 데이터 조회
        logging.info("Barcode_Flow 조회 (SF50)")
        barcode_data_sf50 = db.session.query(
            Barcode_Flow.INSRT_DT
        ).filter(
            Barcode_Flow.BOX_NUM == BOX_NUM,
            Barcode_Flow.TO_SL_CD == 'SF50'
        ).first()

        logging.info("Barcode_Flow 조회 (SF40)")
        barcode_data_sf40 = db.session.query(
            Barcode_Flow.INSRT_DT
        ).filter(
            Barcode_Flow.BOX_NUM == BOX_NUM,
            Barcode_Flow.TO_SL_CD == 'SF40'
        ).first()

        if not barcode_data_sf50:
            logging.warning(f"Barcode_Flow에서 SF50 데이터 없음. 박스번호: {box_num}")
            return jsonify({'status': 'error', 'message': f'SF50에 해당하는 데이터가 Barcode_Flow에서 없습니다: {box_num}'}), 404

        sf50_date = barcode_data_sf50.INSRT_DT.strftime('%Y-%m-%d') if barcode_data_sf50 else None
        sf40_date = barcode_data_sf40.INSRT_DT.strftime('%Y-%m-%d') if barcode_data_sf40 else None

        logging.info(f"Barcode_Flow 데이터: SF50 날짜={sf50_date}, SF40 날짜={sf40_date}")

        return jsonify({
            'status': 'success',
            'sales_detail': {
                'box_num': BOX_NUM,
                'cs_qty': int(cs_qty),
                'sf50_date': sf50_date,
                'sf40_date': sf40_date
            }
        })

    except Exception as e:
        logging.error(f"sales_detail 처리 중 오류: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '서버 내부 오류가 발생했습니다.'}), 500

# 출하 모델에서 등록 버튼을 누르면 서버로 넘어가는 로직
@bp.route('/sales_register/', methods=['POST'])
def sales_register():
    try:
        data = request.json
        logging.info(f"Received data for sales register: {data}")

        if not data or 'rows' not in data:
            return jsonify({"status": "error", "message": "No data provided"}), 400

        doc_no = generate_doc_no()
        doc_seq = 10
        new_material_docs = []

        for row in data['rows']:
            box_num = row.get('box_num')
            so_no = row.get('so_no')  # 클라이언트에서 전달받은 SO_NO
            so_seq = row.get('so_seq')  # 클라이언트에서 전달받은 SO_SEQ
            bp_cd = row.get('bp_cd')  # 클라이언트에서 전달받은 BP_CD

            if not box_num or not so_no or not so_seq or not bp_cd:
                logging.warning(f"Missing box_num, so_no, so_seq, or bp_cd in row: {row}")
                continue

            # Packing_Cs에서 cs_qty 조회
            packing_cs_entry = db.session.query(Packing_Cs).filter_by(m_box_no=box_num).first()

            if not packing_cs_entry:
                logging.warning(f"No Packing_Cs entry found for box_num={box_num}")
                continue

            # cs_qty를 정수형으로 변환
            try:
                cs_qty = int(packing_cs_entry.cs_qty)
            except ValueError:
                logging.error(f"Invalid cs_qty value for box_num={box_num}: {packing_cs_entry.cs_qty}")
                continue

            # Barcode_Flow에서 TO_SL_CD='SF50' 조건으로 데이터 조회
            barcodes_sf50 = db.session.query(Barcode_Flow).filter(
                Barcode_Flow.BOX_NUM == box_num,
                Barcode_Flow.TO_SL_CD == 'SF50'
            ).all()

            if not barcodes_sf50:
                logging.warning(f"No Barcode_Flow records found for box_num={box_num} with TO_SL_CD='SF50'.")
                continue

            # Barcode_Flow 데이터 생성
            for barcode_entry in barcodes_sf50:
                logging.info(f"Processing barcode entry: {barcode_entry.barcode}")

                new_barcode_flow = Barcode_Flow(
                    barcode=barcode_entry.barcode,  # 기존 바코드 유지
                    ITEM_CD=barcode_entry.ITEM_CD,
                    FROM_SL_CD='SF50',
                    TO_SL_CD='SF60',  # 새로운 목적 창고 코드
                    MOV_TYPE='T01',  # 입고 타입
                    CREDIT_DEBIT='C',
                    REPORT_TYPE='G',
                    SO_NO=so_no,
                    SO_SEQ=so_seq,
                    BP_CD=bp_cd,
                    DOC_NO=doc_no,
                    DOC_SEQ=f"{doc_seq:02}",
                    BOX_NUM=box_num,
                    INSRT_DT=datetime.now(),
                    INSRT_USR=g.user.USR_ID,
                    UPDT_USR=g.user.USR_ID
                )
                db.session.add(new_barcode_flow)

            # Material_Doc 데이터 생성 (Barcode_Flow 루프 밖에서 한 번만 생성)
            new_material_docs.append({
                'DOC_NO': doc_no,
                'DOC_SEQ': f"{doc_seq:02}",
                'ITEM_CD': barcodes_sf50[0].ITEM_CD,  # Barcode_Flow에서 첫 번째 항목의 ITEM_CD 사용
                'CREDIT_DEBIT': 'C',
                'MOV_TYPE': 'T01',
                'QTY': cs_qty,  # Packing_Cs의 cs_qty 사용
                'FROM_SL_CD': 'SF50',
                'TO_SL_CD': 'SF60',
                'REPORT_TYPE': 'G',
                'BOX_NUM': box_num,
                'SO_NO': so_no,
                'SO_SEQ': so_seq,
                'BP_CD': bp_cd,
                'INSRT_DT': datetime.now(),
                'INSRT_USR': g.user.USR_ID,
                'UPDT_DT': datetime.now(),
                'UPDT_USR': g.user.USR_ID
            })

            # Sales_Order 모델의 DLVY_QTY 업데이트
            sales_order_entry = db.session.query(Sales_Order).filter_by(SO_NO=so_no, SO_SEQ=so_seq).first()

            if sales_order_entry:
                if sales_order_entry.DLVY_QTY is None:
                    sales_order_entry.DLVY_QTY = 0
                sales_order_entry.DLVY_QTY += cs_qty
                logging.info(f"Updated DLVY_QTY for SO_NO={so_no}, SO_SEQ={so_seq} to {sales_order_entry.DLVY_QTY}")
            else:
                logging.warning(f"No Sales_Order entry found for SO_NO={so_no}, SO_SEQ={so_seq}")

            doc_seq += 10

        # Material_Doc 데이터 일괄 삽입
        if new_material_docs:
            db.session.bulk_insert_mappings(Material_Doc, new_material_docs)

        db.session.commit()
        return jsonify({"status": "success", "message": f"Sales register completed: {doc_no}"})

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error during sales register: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route('/supply_details/', methods=['GET'])
def supply_details():

    return render_template('sales/supply_details.html',  show_navigation_bar=True)