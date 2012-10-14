"""
The application module for Namake.

This module defines the main WSGI application class.
"""

import re
import logging

from webob import exc, Request, Response

# TODO: Configuration based in ini files.
# TODO: HTTP request error handling based on webob.exc
# TODO: URL Composition (reverse)
# TODO: Logging using the standard logging module.
# TODO: Namake's Request and Response objects.

from .config import Config

logger = logging.getLogger(__name__)

__all__ = (
    'Application',
    'Request',
    'Response',
)

class Application(object):
    request_class = Request
    #: Default configuration parameters.
    default_config = {
        'DEBUG':    False,
    }

    def __init__(self):
        self.routes = []
        self.controller_cache = {}
        self.config = Config()

        # Setup basic logging.
        if not logging.root.handlers and logger.level == logging.NOTSET:
            logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            logger.addHandler(handler)

    def add_route(self, regex, controller, name=None, kwargs=None):
        """
        Adds a url route to the application's routing table.

        Namake's routing is a simple regex based lookup.
        """
        self.routes.append((re.compile(regex),
                            name,
                            controller,
                            kwargs))

    def __call__(self, environ, start_response):
        req = self.request_class(environ)
        for regex, name, controller_path, kwargs in self.routes:
            match = regex.match(req.path_info)
            if match:
                # Get the proper controller
                controller = self.controller_cache.pop(controller_path, None)
                if not controller:
                    if hasattr(controller_path, '__call__'):
                        # The given controller is already a callable. Just use it.
                        controller = controller_path
                        self.controller_cache[controller_path] = controller
                    else:
                        # The controller module hasn't been loaded yet.
                        # Load it here.
                        try:
                            from .utils import import_string
                            controller = import_string(controller_path)
                        except ImportError:
                            # TODO: HTML Tracebacks, Debugging, etc.
                            logger.error("Internal Server Error", exc_info=1)
                            return exc.HTTPServerError()(environ, start_response)

                if controller: 
                    request = Request(environ)

                    # Attach the application to the request so that the
                    # request handler has a copy of it.
                    request.app = self

                    # If there are any named groups, use those as kwargs, ignoring
                    # non-named groups. Otherwise, pass all non-named arguments as
                    # positional arguments.
                    urlkwargs = match.groupdict()
                    if urlkwargs:
                        urlargs = ()
                    else:
                        urlargs = match.groups()

                    # In both cases, pass any extra_kwargs as **kwargs.
                    if kwargs:
                        urlkwargs.update(kwargs)
                    response = controller(request, *urlargs, **urlkwargs)
                    return response(environ, start_response)

        return exc.HTTPNotFound()(environ, start_response)

    def run(self, host='', port=8000, debug=None, **options):
        # For now just use the wsgiref server
        from wsgiref.simple_server import make_server
        httpd = make_server(host, port, self)
        display_hostname = host or 'localhost'
        logger.info(' * Running on http://%s:%d/', display_hostname, port)
        httpd.serve_forever()
