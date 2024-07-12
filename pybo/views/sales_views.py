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

bp = Blueprint('sales', __name__, url_prefix='/sales')

@bp.route('/sales_order/', methods=['GET'])
def sales_order():

    return render_template('sales/sales_order.html',  show_navigation_bar=True)

@bp.route('/supply_details/', methods=['GET'])
def supply_details():

    return render_template('sales/supply_details.html',  show_navigation_bar=True)