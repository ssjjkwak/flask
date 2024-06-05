import os
from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData

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
        basic_views, download_views
    )
    app.register_blueprint(main_views.bp)
    app.register_blueprint(auth_views.bp)
    app.register_blueprint(dashboard_views.bp)
    app.register_blueprint(product_views.bp)
    app.register_blueprint(delivery_views.bp)
    app.register_blueprint(basic_views.bp)
    app.register_blueprint(download_views.bp)

    # Register filters
    from .filter import format_datetime
    app.jinja_env.filters['datetime'] = format_datetime

    return app

def make_shell_context():
    from . import models  # Ensure models are imported
    return {'db': db, 'models': models}

# Ensure the app is created and shell context is set correctly
app = create_app()
app.shell_context_processor(make_shell_context)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
