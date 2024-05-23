from datetime import datetime

from flask import Blueprint, render_template, request, url_for, g, flash
from werkzeug.utils import redirect

from pybo.models import Question, Answer, Users
from pybo.forms import QuestionForm, AnswerForm
from pybo import db
from pybo.views.auth_views import login_required

bp = Blueprint('question', __name__, url_prefix='/question')


@bp.route('/list/')
def _list():
    page = request.args.get('page', type=int, default=1)
    kw = request.args.get('kw', type=str, default='')
    question_list = Question.query.order_by(Question.create_date.desc())
    if kw:
        search = '%%{}%%'.format(kw)
        sub_query = db.session.query(Answer.question_id, Answer.content, Users.username) \
            .join(Users, Answer.users_id == Users.id).subquery()
        question_list = question_list \
            .join(Users) \
            .outerjoin(sub_query, sub_query.c.question_id == Question.id) \
            .filter(Question.code.ilike(search) |  # 질문제목
                    Question.content.ilike(search) |  # 질문내용
                    Users.username.ilike(search) |  # 질문작성자
                    sub_query.c.content.ilike(search) |  # 답변내용
                    sub_query.c.username.ilike(search) | # 답변작성자
                    Question.barcode1.ilike(search) |  # 바코드1
                    Question.barcode2.ilike(search) |  # 바코드2
                    Question.barcode3.ilike(search) |  # 바코드3
                    Question.barcode4.ilike(search) |  # 바코드4
                    Question.barcode5.ilike(search) |  # 바코드5
                    Question.udi_one.ilike(search) |  # UDI 코드 (단위)
                    Question.udi_box.ilike(search) |  # UDI 코드 (박스)
                    Question.qr_code.ilike(search)  # QR 코드
                    ) \
            .distinct()
    question_list = question_list.paginate(page=page, per_page=15)
    return render_template('question/question_list.html', question_list=question_list, page=page, kw=kw, show_navigation_bar=True)


@bp.route('/detail/<int:question_id>/')
def detail(question_id):
    form = AnswerForm()
    question = Question.query.get_or_404(question_id)
    return render_template('question/question_detail.html', question=question, form=form, show_navigation_bar=True)

@bp.route('/create/', methods=('GET','POST'))
@login_required
def create():
    form = QuestionForm()
    if request.method == 'POST' and form.validate_on_submit():
        question = (
            Question(
                makeorder_no=form.makeorder_no.data, code=form.code.data, name=form.name.data,
                barcode1=form.barcode1.data, barcode2=form.barcode2.data, barcode3=form.barcode3.data,
                barcode4=form.barcode4.data, barcode5=form.barcode5.data, udi_one=form.udi_one.data,
                udi_box=form.udi_box.data, qr_code=form.qr_code.data, content=form.content.data,
                create_date=datetime.now(), users=g.user
            )
        )
        db.session.add(question)
        db.session.commit()
        return redirect(url_for('question._list'))
    return render_template('question/question_form.html', form=form, show_navigation_bar=True)

@bp.route('/modify/<int:question_id>', methods=('GET', 'POST'))
@login_required
def modify(question_id):
    question = Question.query.get_or_404(question_id)
    if g.user != question.user:
        flash('수정권한이 없습니다')
        return redirect(url_for('question.detail', question_id=question_id))
    if request.method == 'POST':  # POST 요청
        form = QuestionForm()
        if form.validate_on_submit():
            form.populate_obj(question)
            question.modify_date = datetime.now()  # 수정일시 저장
            db.session.commit()
            return redirect(url_for('question.detail', question_id=question_id))
    else:  # GET 요청
        form = QuestionForm(obj=question)
    return render_template('question/question_form.html', form=form)

@bp.route('/delete/<int:question_id>')
@login_required
def delete(question_id):
    question = Question.query.get_or_404(question_id)
    if g.user != question.user:
        flash('삭제권한이 없습니다')
        return redirect(url_for('question.detail', question_id=question_id))
    db.session.delete(question)
    db.session.commit()
    return redirect(url_for('question._list'))
