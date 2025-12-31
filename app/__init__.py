from flask import Flask, session
from pymongo import MongoClient
from pymongo.collection import Collection
from flask_session import Session
from flask_session.sessions import MongoDBSessionInterface, want_bytes
import types
import os
from datetime import datetime, timedelta, timezone


# Global MongoDB client
mongo_client = None
db = None


def get_db():
    """Return initialized MongoDB database handle"""
    if db is None:
        raise RuntimeError("Database not initialized. Call create_app first.")
    return db


def create_app(config_name='default'):
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    from config import config
    app.config.from_object(config[config_name])

    # Compatibility patch: pymongo 4 removed Collection.update used by Flask-Session
    if not hasattr(Collection, 'update'):
        def _legacy_update(self, spec, document, upsert=False, multi=False, **kwargs):
            # Flask-Session on PyMongo 4 passes full replacement docs (no $ operators)
            # If the doc contains $ operators, delegate to update_one/update_many
            has_operator = any(key.startswith('$') for key in document.keys())

            if has_operator:
                if multi:
                    return self.update_many(spec, document, upsert=upsert, **kwargs)
                return self.update_one(spec, document, upsert=upsert, **kwargs)

            # Replacement-style: use replace_one with upsert to match legacy behavior
            return self.replace_one(spec, document, upsert=upsert, **kwargs)

        Collection.update = _legacy_update
    
    # Initialize MongoDB
    init_db(app)
    
    # Initialize Flask-Session
    app.config['SESSION_MONGODB'] = mongo_client
    app.config['SESSION_MONGODB_DB'] = app.config['DB_NAME']
    app.config['SESSION_MONGODB_COLLECTION'] = 'sessions'
    Session(app)

    # Patch MongoDBSessionInterface to ensure cookie value is str (not bytes)
    if isinstance(app.session_interface, MongoDBSessionInterface):
        original_save = app.session_interface.save_session

        def _patched_save_session(self, app_ctx, session_obj, response):
            domain = self.get_cookie_domain(app_ctx)
            path = self.get_cookie_path(app_ctx)
            store_id = self.key_prefix + session_obj.sid
            if not session_obj:
                if session_obj.modified:
                    self.store.remove({'id': store_id})
                    response.delete_cookie(app_ctx.config["SESSION_COOKIE_NAME"],
                                           domain=domain, path=path)
                return

            conditional_cookie_kwargs = {}
            httponly = self.get_cookie_httponly(app_ctx)
            secure = self.get_cookie_secure(app_ctx)
            if hasattr(self, "get_cookie_samesite"):
                conditional_cookie_kwargs["samesite"] = self.get_cookie_samesite(app_ctx)
            expires = self.get_expiration_time(app_ctx, session_obj)
            val = self.serializer.dumps(dict(session_obj))
            self.store.update({'id': store_id},
                              {'id': store_id,
                               'val': val,
                               'expiration': expires}, True)
            if self.use_signer:
                session_id = self._get_signer(app_ctx).sign(want_bytes(session_obj.sid))
                if isinstance(session_id, bytes):
                    session_id = session_id.decode()
            else:
                session_id = session_obj.sid
            response.set_cookie(app_ctx.config["SESSION_COOKIE_NAME"], session_id,
                                expires=expires, httponly=httponly,
                                domain=domain, path=path, secure=secure,
                                **conditional_cookie_kwargs)

        app.session_interface.save_session = types.MethodType(_patched_save_session, app.session_interface)

        # Also patch open_session to handle None expiration values
        original_open = app.session_interface.open_session

        def _patched_open_session(self, app_ctx, request):
            s_id = request.cookies.get(app_ctx.config["SESSION_COOKIE_NAME"])
            if not s_id:
                s_id = self._generate_sid()
                return self.session_class(sid=s_id, permanent=self.permanent)
            if self.use_signer:
                signer = self._get_signer(app_ctx)
                try:
                    s_id = signer.unsign(want_bytes(s_id))
                    # Ensure s_id is a string, not bytes
                    if isinstance(s_id, bytes):
                        s_id = s_id.decode('utf-8')
                except Exception:
                    s_id = self._generate_sid()
                    return self.session_class(sid=s_id, permanent=self.permanent)
            
            # Ensure s_id is string before concatenation
            if isinstance(s_id, bytes):
                s_id = s_id.decode('utf-8')
            
            store_id = self.key_prefix + s_id
            document = self.store.find_one({"id": store_id})
            
            # CRITICAL FIX: Check if document exists AND has a non-None expiration before comparing
            if document:
                expiration = document.get("expiration")
                # If expiration is None or is in the past, delete the session
                # MongoDB stores naive UTC datetimes, so compare with naive datetime
                if expiration is None or expiration <= datetime.utcnow():
                    self.store.delete_one({"id": store_id})
                    s_id = self._generate_sid()
                    return self.session_class(sid=s_id, permanent=self.permanent)
                
                val = document.get("val")
                data = self.serializer.loads(want_bytes(val))
                return self.session_class(data, sid=s_id)
            
            # No document found, create new session
            s_id = self._generate_sid()
            return self.session_class(sid=s_id, permanent=self.permanent)

        app.session_interface.open_session = types.MethodType(_patched_open_session, app.session_interface)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Context processors
    @app.context_processor
    def inject_user():
        """Make current user available in all templates"""
        from flask import session as flask_session
        from app.models.user import User
        user_id = flask_session.get('user_id') if flask_session else None
        user = User.get_by_id(user_id) if user_id else None
        return {'current_user': user}
    
    @app.context_processor
    def inject_company():
        """Make company info available in templates"""
        return {
            'company_name': app.config['COMPANY_NAME'],
            'company_gstin': app.config['COMPANY_GSTIN'],
            'company_address': app.config['COMPANY_ADDRESS'],
            'company_email': app.config['COMPANY_EMAIL'],
            'company_phone': app.config['COMPANY_PHONE']
        }
    
    return app


def init_db(app):
    """Initialize MongoDB connection"""
    global mongo_client, db
    mongo_client = MongoClient(app.config['MONGO_URI'])
    db = mongo_client[app.config['DB_NAME']]
    
    # Create indexes
    db.users.create_index('email', unique=True)
    db.clients.create_index('company_name')
    db.invoices.create_index('invoice_no', unique=True)
    db.invoices.create_index('client_id')
    db.products.create_index('name')
    
    app.db = db


def register_blueprints(app):
    """Register all blueprints"""
    from app.routes.public import public_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.invoices import invoices_bp
    from app.routes.clients import clients_bp
    from app.routes.products import products_bp
    
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(invoices_bp, url_prefix='/invoices')
    app.register_blueprint(clients_bp, url_prefix='/clients')
    app.register_blueprint(products_bp, url_prefix='/products')


def register_error_handlers(app):
    """Register error handlers"""
    
    @app.errorhandler(404)
    def not_found(error):
        from flask import render_template
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(403)
    def forbidden(error):
        from flask import render_template
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        return render_template('errors/500.html'), 500
