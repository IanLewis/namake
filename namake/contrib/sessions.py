from beaker.middleware import SessionMiddleware

class Sessions(object):
    """
    An extension for Namake that provides support for sessions
    using the beaker library.
    """

    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        self.app = app
        app.sessions = self
        app.extensions['sessions'] = self

        app.config.setdefault('SESSION_TYPE', 'cookie')
        app.config.setdefault('SESSION_COOKIE_EXPIRES', True)
        app.config.setdefault('SESSION_SECRET', app.config['SECRET_KEY'])

        # Wrap the application with the beaker session middleware.
        app.wsgi_app = SessionMiddleware(app.wsgi_app, {
            'session.type': app.config['SESSION_TYPE'],
            'session.cookie_expires': app.config['SESSION_COOKIE_EXPIRES'],
            'session.secret': app.config['SESSION_SECRET'],
            'session.validate_key': app.config['SESSION_SECRET'],
        })
        self.app.before_request(self.before_request)
        self.app.after_request(self.after_request)
    
    def before_request(self, request):
        """
        Adds the session object to the request.session property.
        """
        request.session = request.environ['beaker.session']

    def after_request(self, request, response):
        """
        Saves the session automatically after request processing.
        """
        if hasattr(request, 'session'):
            request.session.save()
