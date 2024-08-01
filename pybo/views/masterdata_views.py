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
@bp.route('/bom/', methods=['GET', 'POST'])
def bom():

    return render_template('masterdata/bom.html', show_navigation_bar=True)

#거래처정보조회
@bp.route('/vendor/', methods=['GET', 'POST'])
def vendor():

    return render_template('masterdata/vendor.html', show_navigation_bar=True)