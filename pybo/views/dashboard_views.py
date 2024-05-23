from datetime import datetime

from flask import Blueprint, render_template, request, url_for, g, flash
from werkzeug.utils import redirect

from pybo.models import Question, Answer, Users
from pybo.forms import QuestionForm, AnswerForm
from pybo import db
from pybo.views.auth_views import login_required

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@bp.route('/')
def dashboard():

    return render_template('dashboard.html')