from flask import Blueprint, render_template

bp = Blueprint('question', __name__, url_prefix='/question')

@bp.route('/list/')
def _list():
    # 임시 데이터로 빈 리스트와 기본 값 설정
    question_list = []
    page = 1
    kw = ''
    return render_template('question/question_list.html', question_list=question_list, page=page, kw=kw, show_navigation_bar=True)

@bp.route('/detail/<int:question_id>/')
def detail(question_id):
    # 임시 데이터로 기본 값 설정
    question = {}
    form = None
    return render_template('question/question_detail.html', question=question, form=form, show_navigation_bar=True)

@bp.route('/create/', methods=('GET', 'POST'))
def create():
    # 임시 데이터로 기본 값 설정
    form = None
    return render_template('question/question_form.html', form=form, show_navigation_bar=True)

@bp.route('/modify/<int:question_id>', methods=('GET', 'POST'))
def modify(question_id):
    # 임시 데이터로 기본 값 설정
    form = None
    return render_template('question/question_form.html', form=form)

# @bp.route('/delete/<int:question_id>')
# def delete(question_id):
#     # 삭제 엔드포인트도 최소한의 내용으로 정의
#     return redirect(url_for('question._list'))
