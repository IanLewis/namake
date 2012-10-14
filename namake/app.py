"""
The application module for Namake.

This module defines the main WSGI application class.
"""

import re
import sys
import os
import pkgutil
import logging

from webob import exc, Request, Response

# TODO: Reloading local development server.
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

def get_root_path(import_name):
    """Returns the path to a package or cwd if that cannot be found.  This
    returns the path of a package or the folder that contains a module.

    Not to be confused with the package path returned by :func:`find_package`.
    """
    # Module already imported and has a file attribute.  Use that first.
    mod = sys.modules.get(import_name)
    if mod is not None and hasattr(mod, '__file__'):
        return os.path.dirname(os.path.abspath(mod.__file__))

    # Next attempt: check the loader.
    loader = pkgutil.get_loader(import_name)

    # Loader does not exist or we're referring to an unloaded main module
    # or a main module without path (interactive sessions), go with the
    # current working directory.
    if loader is None or import_name == '__main__':
        return os.getcwd()

    # For .egg, zipimporter does not have get_filename until Python 2.7.
    # Some other loaders might exhibit the same behavior.
    if hasattr(loader, 'get_filename'):
        filepath = loader.get_filename(import_name)
    else:
        # Fall back to imports.
        __import__(import_name)
        filepath = sys.modules[import_name].__file__

    # filepath is import_name.py for a module, or __init__.py for a package.
    return os.path.dirname(os.path.abspath(filepath))

def repl_start_response(start_response, parent_exc_info):
    """
    A wrapper for the WSGI start_response callable that
    ensures we pass the exc_info to the callable.
    """
    def _wrapped(status, headers, exc_info=None):
        if exc_info is None:
            exc_info = parent_exc_info
        return start_response(status, headers, exc_info)
    return _wrapped

class Application(object):
    """
    The main application class.
    """

    request_class = Request
    response_class = Response

    def __init__(self, import_name):
        self.routes = []
        self.controller_cache = {}
        self.root_path = get_root_path(import_name)
        self.config = Config(self.root_path, 
                             defaults=self.get_default_config())

        # Setup basic logging.
        if not logging.root.handlers and logger.level == logging.NOTSET:
            logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            logger.addHandler(handler)

    def get_default_config(self):
        """
        Default configuration parameters.
        Can be overridden by mixins or subclasses to add new options.
        """
        return {
            'DEBUG': False,
        }

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
        request = self.request_class(environ)

        # Attach the application to the request so that the
        # request handler has a copy of it.
        request.app = self

        for regex, name, controller_path, kwargs in self.routes:
            match = regex.match(request.path_info)
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

                try:
                    response = self.handle_request(request, controller, urlargs, urlkwargs)
                except Exception, e:
                    # An exception has occurred. 
                    exc_info = sys.exc_info()
                    response = self.handle_exception(request, e, exc_info)
                    start_response = repl_start_response(start_response, exc_info)

                return response(environ, start_response)

        # No matching URLs. Return A 404.
        return self.handle_exception(request, exc.HTTPNotFound())(environ, start_response)
    
    def handle_request(self, request, controller, args, kwargs):
        """
        Handles a request via the given controller.
        """
        return self.make_response(request, controller(request, *args, **kwargs))

    def handle_exception(self, request, e, exc_info=None):
        if isinstance(e, exc.HTTPException):
            if isinstance(e, exc.HTTPServerError):
                logger.error("HTTP Server Error", exc_info=1)
            return e
        else:
            logger.error("Internal Server Error", exc_info=1)
            if self.config['DEBUG']:
                from .debug import DebugHTTPInternalServerError
                return DebugHTTPInternalServerError(exc_info=exc_info)
            else:
                return exc.HTTPInternalServerError()

    def make_response(self, request, rv):
        """Converts the return value from a view function to a real
        response object that is an instance of :attr:`response_class`.

        The following types are allowed for `rv`:

        .. tabularcolumns:: |p{3.5cm}|p{9.5cm}|

        ======================= ===========================================
        :attr:`response_class`  the object is returned unchanged
        :class:`str`            a response object is created with the
                                string as body
        :class:`unicode`        a response object is created with the
                                string encoded to utf-8 as body
        a WSGI function         the function is called as WSGI application
                                and buffered as response object
        :class:`tuple`          A tuple in the form ``(response, status,
                                headers)`` where `response` is any of the
                                types defined here, `status` is a string
                                or an integer and `headers` is a list of
                                a dictionary with header values.
        ======================= ===========================================

        :param rv: the return value from the view function

        .. versionchanged:: 0.9
           Previously a tuple was interpreted as the arguments for the
           response object.
        """
        status = headers = None
        if isinstance(rv, tuple):
            rv, status, headers = rv + (None,) * (3 - len(rv))

        if rv is None:
            raise ValueError('View function did not return a response')

        if not isinstance(rv, self.response_class):
            # When we create a response object directly, we let the constructor
            # set the headers and status.  We do this because there can be
            # some extra logic involved when creating these objects with
            # specific values (like defualt content type selection).
            if isinstance(rv, basestring):
                rv = self.response_class(rv, headerlist=headers, status=status)
                headers = status = None

        if status is not None:
            if isinstance(status, basestring):
                rv.status = status
            else:
                rv.status_int = status
        if headers:
            rv.headerlist.extend(headers)

        return rv

    def run(self, host='', port=8000, debug=None, **options):
        # For now just use the wsgiref server
        from wsgiref.simple_server import make_server
        httpd = make_server(host, port, self)
        display_hostname = host or 'localhost'
        logger.info(' * Running on http://%s:%d/', display_hostname, port)
        httpd.serve_forever()
