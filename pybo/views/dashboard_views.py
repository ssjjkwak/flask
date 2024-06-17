from datetime import datetime

from flask import Blueprint, render_template, request, url_for, g, flash, session
from werkzeug.utils import redirect

from pybo.models import User
from pybo.forms import QuestionForm, AnswerForm
from pybo import db
from pybo.views.auth_views import login_required

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@bp.route('/')
def dashboard():
    if 'logged_in' in session and session['logged_in']:
        return render_template('dashboard.html', username=session['USR_ID'])
    else:
        return redirect(url_for('auth.login'))