from flask import Blueprint, url_for, session
from werkzeug.utils import redirect


bp = Blueprint('main', __name__, url_prefix='/')


@bp.route('/hello')
def hello_pybo():
    return 'Hello, World !!'

@bp.route('/')
def index():
    if 'logged_in' in session and session['logged_in']:
        return redirect(url_for('dashboard.dashboard'))
    else:
        return redirect(url_for('auth.login'))







