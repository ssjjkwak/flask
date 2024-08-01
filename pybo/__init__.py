import os
from flask import Flask, render_template
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from sqlalchemy.exc import IntegrityError, ProgrammingError, InvalidRequestError, PendingRollbackError, DataError, \
    ResourceClosedError, StatementError, DisconnectionError, OperationalError
import config


# Naming convention for SQLAlchemy
naming_convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize extensions
db = SQLAlchemy(metadata=MetaData(naming_convention=naming_convention))
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(config)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # Set the upload folder
    app.jinja_env.globals.update(zip=zip)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Import models inside app context
    with app.app_context():
        from . import models

    # Register blueprints
    from .views import (
        main_views, auth_views,
        dashboard_views, product_views, delivery_views,
        basic_views, download_views, sales_views, inventory_views, masterdata_views
    )
    app.register_blueprint(main_views.bp)
    app.register_blueprint(auth_views.bp)
    app.register_blueprint(dashboard_views.bp)
    app.register_blueprint(product_views.bp)
    app.register_blueprint(delivery_views.bp)
    app.register_blueprint(basic_views.bp)
    app.register_blueprint(download_views.bp)
    app.register_blueprint(sales_views.bp)
    app.register_blueprint(inventory_views.bp)
    app.register_blueprint(masterdata_views.bp)


    from .filter import format_datetime
    app.jinja_env.filters['datetime'] = format_datetime
    app.jinja_env.filters['none_to_dash'] = none_to_dash

    # @app.errorhandler(Exception)
    # def handle_exception(e):
    #     # If the exception is related to SQLAlchemy, rollback the session
    #     if isinstance(e, (
    #             IntegrityError, PendingRollbackError, OperationalError,
    #             ProgrammingError, DataError, TimeoutError, DisconnectionError,
    #             InvalidRequestError, ResourceClosedError, StatementError
    #     )):
    #         db.session.rollback()
    #
    #     # 전달할 오류 메시지를 설정합니다.
    #     error_message = str(e)
    #     # 오류 페이지를 렌더링합니다.
    #     return render_template('error.html', error_message=error_message), 500

    return app

def make_shell_context():
    from . import models  # Ensure models are imported
    return {'db': db, 'models': models}

def none_to_dash(value):
    return value if value is not None else ''


# Ensure the app is created and shell context is set correctly
app = create_app()
app.shell_context_processor(make_shell_context)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001)
