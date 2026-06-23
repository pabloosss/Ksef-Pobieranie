from flask import Flask
from .config import SECRET_KEY, LEAVE_TYPES
from .db import init_db
from .helpers import pl_date, is_hr, is_manager
from .routes import register_routes
from .routes_extra import register_extra_routes


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.secret_key = SECRET_KEY
    init_db()
    app.template_filter("pldate")(pl_date)

    @app.context_processor
    def inject():
        return {"is_hr": is_hr, "is_manager": is_manager, "leave_types": LEAVE_TYPES}

    register_routes(app)
    register_extra_routes(app)
    return app
