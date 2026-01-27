import os
from flask import Flask
from app.config import get_config
from app.extensions import db, migrate, login_manager
from app.models import User

def create_app():
    if os.getenv("FLASK_ENV") != "production":
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except Exception:
            pass

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(get_config())

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app.models import User  # importa aquí para evitar imports tempranos

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))  # SQLAlchemy 2.x style

    from app.blueprints.public.routes import public_bp
    from app.blueprints.admin.routes import admin_bp
    from app.blueprints.checkout.routes import checkout_bp
    from app.blueprints.payments.routes import payments_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(checkout_bp, url_prefix="/checkout")
    app.register_blueprint(payments_bp)

    from app.cli import register_cli
    register_cli(app)

    return app


