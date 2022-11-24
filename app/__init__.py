

from flask import Flask
from flask_bootstrap import Bootstrap5
from flask_login import LoginManager
from flask_marshmallow import Marshmallow

from config import Config

bootstrap = Bootstrap5()
login = LoginManager()
ma = Marshmallow()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    bootstrap.init_app(app)
    login.login_view = 'main.login'
    login.init_app(app)
    ma.init_app(app)

    from . main import bp as main_bp
    app.register_blueprint(main_bp)

    from . api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api') 
        
    return app


