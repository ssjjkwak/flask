import pandas as pd
from flask import Blueprint, url_for, render_template, flash, request, session, g, app, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import redirect, send_file

from pybo import db
from pybo.forms import UserCreateForm, UserLoginForm, UserModifyForm, UserUpdateForm
from pybo.models import User, Role
import functools

from pybo.views.download_views import convert_to_excel

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/signup/', methods=('GET', 'POST'))
def signup():
    form = UserCreateForm()
    if request.method == 'POST' and form.validate_on_submit():
        user = User.query.filter_by(USR_ID=form.USR_ID.data).first()
        if not user:
            user = User(USR_ID=form.USR_ID.data,
                        USR_PW=generate_password_hash(form.USR_PW1.data),
                        USR_EMAIL=form.USR_EMAIL.data, USR_NM=form.USR_NM.data, USR_JOB=form.USR_JOB.data,
                        USR_DEPT=form.USR_DEPT.data, USR_PHONE=form.USR_PHONE.data)
            db.session.add(user)
            db.session.commit()

            # role_id = form.role_name.data  # 폼에서 선택된 권한 ID
            # user_role = Users_Roles(users_id=user.users_id, roles_id=role_id)
            # db.session.add(user_role)
            # db.session.commit()

            return redirect(url_for('main.index'))
        else:
            flash('이미 존재하는 사용자입니다.')
    return render_template('auth/signup.html', form=form, show_navigation_bar=True)

# @bp.route('/login/', methods=('GET', 'POST'))
# def login():
#     form = UserLoginForm()
#     if request.method == 'POST' and form.validate_on_submit():
#         error = None
#         user = User.query.filter_by(USR_ID=form.USR_ID.data).first()
#         if not user:
#             error = "존재하지 않는 사용자입니다."
#         elif not check_password_hash(user.USR_PW, form.USR_PW.data):
#             error = "비밀번호가 올바르지 않습니다."
#         if error is None:
#             session.clear()
#             session['USR_ID'] = user.USR_ID
#
#             # 사용자의 roles_id를 세션에 저장
#             # user_role = Users_Roles.query.filter_by(users_id=user.users_id).first()
#             # if user_role:
#             #     session['roles_id'] = user_role.roles_id
#             #
#             # _next = request.args.get('next', '')
#             # if _next:
#             #     return redirect(_next)
#             # else:
#             #     return redirect(url_for('main.index'))
#         flash(error)
#     return render_template('auth/login.html', form=form, show_navigation_bar=False)


@bp.route('/login/', methods=('GET', 'POST'))
def login():
    form = UserLoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        error = None
        user = User.query.filter_by(USR_ID=form.USR_ID.data).first()
        if not user:
            error = "존재하지 않는 사용자입니다."
        elif not check_password_hash(user.USR_PW, form.USR_PW.data):
            error = "비밀번호가 올바르지 않습니다."

        if error is None:
            session.clear()
            session['logged_in'] = True
            session['USR_ID'] = user.USR_ID  # 수정된 부분: user.USR_ID를 세션에 저장
        return redirect(url_for('main.index'))

    return render_template('auth/login.html', form=form, show_navigation_bar=False)


@bp.before_app_request
def load_logged_in_user():
    users_id = session.get('USR_ID')
    if users_id is None:
        g.user = None
    else:
        g.user = User.query.get(users_id)

@bp.route('/logout/')
def logout():
    session.clear()
    return redirect(url_for('main.index'))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            _next = request.url if request.method == 'GET' else ''
            return redirect(url_for('auth.login', next=_next))
        return view(*args, **kwargs)
    return wrapped_view

@bp.route('/modify/', methods=('GET','POST'))
@login_required
def modify():
    form = UserModifyForm()
    if request.method == 'POST' and form.validate_on_submit():
        # 현재 로그인한 사용자를 가져옴
        user = g.user

        # 현재 비밀번호가 맞는지 확인
        if user and check_password_hash(user.password, form.old_password.data):
            # 새 비밀번호로 업데이트
            user.password = generate_password_hash(form.new_password1.data)
            db.session.commit()
            flash('비밀번호가 변경되었습니다.')
            return redirect(url_for('main.index'))  # 비밀번호 변경 후 리다이렉트 할 위치
        else:
            flash('현재 비밀번호가 올바르지 않습니다.')
    return render_template('auth/modify.html', form=form, show_navigation_bar=True)


@bp.route('/user_manage')
def user_manage():
    users = User.query.all()
    roles = {role.ROLE_ID: role.ROLE_NM for role in Role.query.all()}

    users_with_roles = [
        {
            'USR_ID': user.USR_ID,
            'USR_NM': user.USR_NM,
            'USR_EMAIL': user.USR_EMAIL,
            'USR_DEPT': user.USR_DEPT,
            'USR_JOB': user.USR_JOB,
            'USR_PHONE': user.USR_PHONE,
            'ROLES': [roles.get(user.ROLE_ID, 'N/A')],
            'INSRT_DT': user.INSRT_DT.strftime('%Y-%m-%d'),
            'UPDT_DT': user.UPDT_DT.strftime('%Y-%m-%d'),
        }
        for user in users
    ]

    total_users = len(users_with_roles)

    return render_template('auth/user_manage.html', users_with_roles=users_with_roles, total_users=total_users)


@bp.route('/user_update/<string:USR_ID>', methods=['GET', 'POST'])
def user_update(USR_ID):
    user = User.query.get(USR_ID)
    if user is None:
        # 사용자 ID가 잘못된 경우에 대한 처리
        return redirect(url_for('main.index'))

    form = UserUpdateForm(obj=user)  # 사용자 데이터로 폼을 미리 채움
    if request.method == 'POST' and form.validate_on_submit():
        user.USR_ID = form.USR_ID.data
        user.USR_NM = form.USR_NM.data
        user.USR_EMAIL = form.USR_EMAIL.data
        if form.USR_PW1.data:
            user.USR_PW = generate_password_hash(form.USR_PW1.data)  # 비밀번호 해싱
        user.USR_DEPT = form.USR_DEPT.data
        user.USR_JOB = form.USR_JOB.data
        user.USR_PHONE = form.USR_PHONE.data
        db.session.commit()
        return redirect(url_for('auth.user_manage'))  # 사용자 관리 페이지로 리디렉션

    return render_template('auth/user_update.html', form=form, user=user)


@bp.route('/user_role', methods=['GET', 'POST'])
def user_role():
    # 임시 데이터로 빈 리스트와 기본 값 설정
    roles = []
    users_with_roles = []

    if request.method == 'POST':
        # 임시로 POST 요청 처리 부분도 정의
        user_id = request.form.get('user_id')
        new_role_id = request.form.get('role_id')
        # 실제 DB 작업 없이 임시로 처리
        print(f"User ID: {user_id}, New Role ID: {new_role_id}")
        return redirect(url_for('auth.user_role'))

    return render_template('auth/user_role.html', users_with_roles=users_with_roles, roles=roles)


@bp.route('/role_permission/', methods=['GET', 'POST'])
def role_permission():
    # 임시 데이터로 기본 값 설정
    admin_count = 0
    mid_manager_count = 0
    user_count = 0

    return render_template('auth/role_permission.html', admin_count=admin_count, mid_manager_count=mid_manager_count, user_count=user_count)



