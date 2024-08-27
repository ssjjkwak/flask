from sqlite3 import IntegrityError

import pandas as pd
from flask import Blueprint, url_for, render_template, flash, request, session, g, app, jsonify
from sqlalchemy import func, literal_column, cast, String
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import redirect, send_file

from pybo import db
from pybo.forms import UserCreateForm, UserLoginForm, UserModifyForm, UserUpdateForm
from pybo.models import User, Role, UserRole
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



            return redirect(url_for('main.index'))
        else:
            flash('이미 존재하는 사용자입니다.')
    return render_template('auth/signup.html', form=form, show_navigation_bar=True)




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

def has_role(user, role_id):
    return any(user_role.role.ROLE_ID == role_id for user_role in user.user_roles)

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('USR_ID')
    if user_id is None:
        g.user = None
        g.user_has_mesauth = False
    else:
        g.user = User.query.get(user_id)
        g.user_has_mesauth = has_role(g.user, 'MESAUTH')

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
        if user and check_password_hash(user.USR_PW, form.old_USR_PW.data):
            # 새 비밀번호로 업데이트
            user.USR_PW = generate_password_hash(form.new_USR_PW1.data)
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
            'ROLES': [{'ROLE_ID': user_role.ROLE_ID, 'ROLE_NM': roles[user_role.ROLE_ID]} for user_role in user.user_roles],
            'INSRT_DT': user.INSRT_DT.strftime('%Y-%m-%d'),
            'UPDT_DT': user.UPDT_DT.strftime('%Y-%m-%d'),
        }
        for user in users
    ]

    total_users = len(users_with_roles)
    all_roles = Role.query.all()  # 모든 권한 정보를 가져옴

    return render_template('auth/user_manage.html', users_with_roles=users_with_roles, total_users=total_users, all_roles=all_roles)


@bp.route('/user_account', methods=['GET'])
def user_account():
    users_with_roles = db.session.query(
        User.USR_ID, User.USR_NM, User.USR_DEPT, User.USR_JOB, User.USR_EMAIL, User.INSRT_DT, User.UPDT_DT,
        func.string_agg(cast(Role.ROLE_NM, String), literal_column("','")).label('ROLES')
    ).outerjoin(UserRole, User.USR_ID == UserRole.USR_ID).outerjoin(Role, UserRole.ROLE_ID == Role.ROLE_ID).group_by(
        User.USR_ID, User.USR_NM, User.USR_DEPT, User.USR_JOB, User.USR_EMAIL, User.INSRT_DT, User.UPDT_DT).all()

    total_users = db.session.query(User).count()
    all_roles = Role.query.all()
    return render_template('auth/user_account.html', users_with_roles=users_with_roles, total_users=total_users, all_roles=all_roles)



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
    roles = Role.query.all()
    roles_data = [
        {
            'ROLE_ID': role.ROLE_ID,
            'ROLE_NM': role.ROLE_NM,
            'REMARK': role.REMARK
        }
        for role in roles
    ]
    return render_template('auth/user_role.html', roles_data=roles_data)



@bp.route('/create_role', methods=['POST'])
def create_role():
    role_id = request.form['role_id']
    role_nm = request.form['role_nm']
    remark = request.form['remark']

    new_role = Role(ROLE_ID=role_id, ROLE_NM=role_nm, REMARK=remark, INSRT_DT=db.func.now(), UPDT_DT=db.func.now())

    try:
        db.session.add(new_role)
        db.session.commit()
        # flash('권한이 성공적으로 생성되었습니다.', 'success')
    except IntegrityError:
        db.session.rollback()
        # flash('권한 생성 중 오류가 발생했습니다. Role 아이디가 이미 존재할 수 있습니다.', 'danger')

    return redirect(url_for('auth.user_role'))


@bp.route('/delete_roles', methods=['POST'])
def delete_roles():
    role_ids = request.form.getlist('role_ids')

    if not role_ids:
        flash('삭제할 권한을 선택해주세요.', 'warning')
    else:
        try:
            Role.query.filter(Role.ROLE_ID.in_(role_ids)).delete(synchronize_session='fetch')
            db.session.commit()
            # flash('선택된 권한이 성공적으로 삭제되었습니다.', 'success')
        except IntegrityError:
            db.session.rollback()
            # flash('권한 삭제 중 오류가 발생했습니다.', 'danger')

    return redirect(url_for('auth.user_role'))


@bp.route('/update_user_roles', methods=['POST'])
def update_user_roles():
    user_id = request.form['user_id']
    new_role_ids = request.form.getlist('newRoles')

    try:
        for new_role_id in new_role_ids:
            new_user_role = UserRole(USR_ID=user_id, ROLE_ID=new_role_id, INSRT_DT=db.func.now(), UPDT_DT=db.func.now())
            db.session.add(new_user_role)
        db.session.commit()
        # flash('권한이 성공적으로 추가되었습니다.', 'success')
    except IntegrityError:
        db.session.rollback()
        #  flash('권한 추가 중 오류가 발생했습니다. 권한이 이미 존재할 수 있습니다.', 'danger')

    return redirect(url_for('auth.user_manage'))



@bp.route('/delete_user_roles', methods=['POST'])
def delete_user_roles():
    user_id = request.form['user_id']
    roles_to_delete = request.form.getlist('roles')

    if not user_id or not roles_to_delete:
        # flash('사용자 ID 또는 권한이 선택되지 않았습니다.', 'warning')
        return redirect(url_for('auth.user_manage'))

    try:
        UserRole.query.filter(UserRole.USR_ID == user_id, UserRole.ROLE_ID.in_(roles_to_delete)).delete(synchronize_session='fetch')
        db.session.commit()
        # flash('권한이 성공적으로 삭제되었습니다.', 'success')
    except IntegrityError:
        db.session.rollback()
        # flash('권한 삭제 중 오류가 발생했습니다.', 'danger')

    return redirect(url_for('auth.user_manage'))










