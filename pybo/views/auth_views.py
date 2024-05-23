import pandas as pd
from flask import Blueprint, url_for, render_template, flash, request, session, g, app, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import redirect, send_file

from pybo import db
from pybo.forms import UserCreateForm, UserLoginForm, UserModifyForm, UserUpdateForm
from pybo.models import Users, Roles, Users_Roles
import functools

from pybo.views.download_views import convert_to_excel

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/signup/', methods=('GET', 'POST'))
def signup():
    form = UserCreateForm()
    if request.method == 'POST' and form.validate_on_submit():
        user = Users.query.filter_by(username=form.username.data).first()
        if not user:
            user = Users(username=form.username.data,
                        password=generate_password_hash(form.password1.data),
                        email=form.email.data, name=form.name.data, jobtitle=form.jobtitle.data,
                        department=form.department.data, phonenumber=form.phonenumber.data)
            db.session.add(user)
            db.session.commit()

            role_id = form.role_name.data  # 폼에서 선택된 권한 ID
            user_role = Users_Roles(users_id=user.users_id, roles_id=role_id)
            db.session.add(user_role)
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
        user = Users.query.filter_by(username=form.username.data).first()
        if not user:
            error = "존재하지 않는 사용자입니다."
        elif not check_password_hash(user.password, form.password.data):
            error = "비밀번호가 올바르지 않습니다."
        if error is None:
            session.clear()
            session['users_id'] = user.users_id

            # 사용자의 roles_id를 세션에 저장
            user_role = Users_Roles.query.filter_by(users_id=user.users_id).first()
            if user_role:
                session['roles_id'] = user_role.roles_id

            _next = request.args.get('next', '')
            if _next:
                return redirect(_next)
            else:
                return redirect(url_for('main.index'))
        flash(error)
    return render_template('auth/login.html', form=form, show_navigation_bar=False)

@bp.before_app_request
def load_logged_in_user():
    users_id = session.get('users_id')
    if users_id is None:
        g.user = None
    else:
        g.user = Users.query.get(users_id)

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
    users_with_roles = db.session.query(Users, Roles.rolename)\
        .select_from(Users)\
        .join(Users_Roles, Users.users_id == Users_Roles.users_id)\
        .join(Roles, Users_Roles.roles_id == Roles.roles_id)\
        .all()
    total_users = len(users_with_roles)
    return render_template('auth/user_manage.html', users_with_roles=users_with_roles, total_users=total_users)


@bp.route('/user_update/<int:user_id>', methods=['GET', 'POST'])
def user_update(user_id):
    user = Users.query.get(user_id)
    form = UserUpdateForm(obj=user)  # Prepopulate the form with user data
    if request.method == 'POST' and form.validate_on_submit():
        user.username = form.username.data
        user.name = form.name.data
        user.email = form.email.data
        user.password = generate_password_hash(form.password1.data)  # 비밀번호 해싱
        user.department = form.department.data
        user.jobtitle = form.jobtitle.data
        user.phonenumber = form.phonenumber.data
        db.session.commit()
        return redirect(url_for('main.index'))

    return render_template('auth/user_update.html', form=form, user=user)

@bp.route('/user_role', methods=['GET', 'POST'])
def user_role():
    roles = db.session.query(Roles).all()  # 모든 권한을 조회
    if request.method == 'POST':
        user_id = request.form['user_id']
        new_role_id = request.form['role_id']
        user_role = Users_Roles.query.filter_by(users_id=user_id).first()
        if user_role:
            user_role.roles_id = new_role_id
        else:
            new_user_role = Users_Roles(users_id=user_id, roles_id=new_role_id)
            db.session.add(new_user_role)
        db.session.commit()
        return redirect(url_for('auth.user_role'))

    users_with_roles = db.session.query(Users, Users_Roles.roles_id). \
        outerjoin(Users_Roles, Users.users_id == Users_Roles.users_id). \
        outerjoin(Roles, Users_Roles.roles_id == Roles.roles_id). \
        all()
    return render_template('auth/user_role.html', users_with_roles=users_with_roles, roles=roles)


@bp.route('/role_permission/', methods=['GET', 'POST'])
def role_permission():
    # Fetch the user count for each specific role
    admin_count = db.session.query(db.func.count(Users_Roles.users_id)).join(Roles).filter(Roles.rolename == 'role_80').scalar()
    mid_manager_count = db.session.query(db.func.count(Users_Roles.users_id)).join(Roles).filter(Roles.rolename == 'role_50').scalar()
    user_count = db.session.query(db.func.count(Users_Roles.users_id)).join(Roles).filter(Roles.rolename == 'role_20').scalar()

    return render_template('auth/role_permission.html', admin_count=admin_count, mid_manager_count=mid_manager_count, user_count=user_count)



