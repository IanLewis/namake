"""
The application module for Namake.

This module defines the main WSGI application class.
"""

import re
import sys
import os
import pkgutil
import logging
from functools import update_wrapper

from webob import Request, Response

# TODO: URL Composition (reverse)
# TODO: Logging using the standard logging module.
# TODO: Namake's Request and Response objects.

from .config import Config

# TODO: Defer logging setup?
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

def setupmethod(f):
    """Wraps a method so that it performs a check in debug mode if the
    first request was already handled.
    """
    def wrapper_func(self, *args, **kwargs):
        if self.config['DEBUG'] and self._got_first_request:
            raise AssertionError('A setup function was called after the '
                'first request was handled.  This usually indicates a bug '
                'in the application where a module was not imported '
                'and decorators or other functionality was called too late.\n'
                'To fix this make sure you call all setup methods, such '
                'as add_route() before serving requests.')
        return f(self, *args, **kwargs)
    return update_wrapper(wrapper_func, f)

class Application(object):
    """
    The main application class.
    """

    request_class = Request
    response_class = Response

    def __init__(self, import_name):
        self.routes = []
        self.controller_cache = {}
        self.extensions = {}
        self._error_handlers = {}
        self._got_first_request = False
        self._before_request_funcs = []
        self._after_request_funcs = []
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
            'SECRET_KEY': None,
        }

    @setupmethod
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
        """Shortcut for :attr:`wsgi_app`."""
        return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ, start_response):
        """
        The actually wsgi application handler. This is maintained
        in the :attr:`wsgi_app` method so that extensions can
        easily add wsgi middleware without loosing a reference
        to the application object.

        So instead of doing this::

            app = MyMiddleware(app)

        It's a better idea to do this instead::

            app.wsgi_app = MyMiddleware(app.wsgi_app)

        Then you still have the original application object around and
        can continue to call methods on it.

        :param environ: a WSGI environment
        :param start_response: a callable accepting a status code,
                               a list of headers and an optional
                               exception context to start the response
        """
        request = self.request_class(environ)

        # Mark the app as having received it's first request.
        self._got_first_request = True

        # Attach the application to the request so that the
        # request handler has a copy of it.
        request.app = self

        # Preprocess the request calling all before_request functions.
        rv = self.preprocess_request(request)
        if rv:
            return self.make_response(request, rv)

        for regex, name, controller_path, kwargs in self.routes:
            match = regex.match(request.path_info)
            if match:
                # Get the proper controller
                try:
                    controller = self.controller_cache.pop(controller_path, None)
                    if not controller:
                        if hasattr(controller_path, '__call__'):
                            # The given controller is already a callable. Just use it.
                            controller = controller_path
                            self.controller_cache[controller_path] = controller
                        else:
                            # The controller module hasn't been loaded yet.
                            # Load it here.
                            from .utils.module import import_string
                            controller = import_string(controller_path)

                    # If there are any named groups, use those as kwargs, ignoring
                    # non-named groups.
                    urlkwargs = match.groupdict()

                    # Pass any extra_kwargs as **kwargs.
                    if kwargs:
                        urlkwargs.update(kwargs)

                    # Call the request handler and return the response.
                    response = self.handle_request(request, controller, urlkwargs)
                    return response(environ, start_response)
                except Exception, e:
                    # An exception has occurred. 
                    exc_info = sys.exc_info()
                    response = self.handle_exception(request, e, exc_info)
                    start_response = repl_start_response(start_response, exc_info)
                    return response(environ, start_response)

        # No matching URLs. Return A 404.
        from webob import exc
        return self.handle_exception(request, exc.HTTPNotFound())(environ, start_response)

    @setupmethod
    def before_request(self, f):
        """
        Registers a function to run before each request.
        These functions are run in the order they are registered.

        Your function must take one parameter, a :attr:`request_class` object
        and return a new request object or the same request object.
        """
        self._before_request_funcs.append(f)
        return f

    @setupmethod
    def after_request(self, f):
        """
        Register a function to be run after each request. Your function
        must take two parameters, a :attr:`request_class` object and a
        :attr:`response_class` object and return a new response object
        or the same object.

        This function will be called at the end of each request
        regardless of if an unhandled exception ocurred in the
        reverse order that it was registered.
        """
        self._after_request_funcs.append(f)
        return f

    def preprocess_request(self, request):
        rv = None
        for func in self._before_request_funcs:
            rv = func(request)
            if rv:
                return rv
    
    def handle_request(self, request, controller, kwargs):
        """
        Handles a request via the given controller.
        """
        return self.make_response(request, controller(request, **kwargs))

    @setupmethod
    def register_error_handler(self, code, f):
        """
        Registers an error handler for the given HTTP status
        code with the application.
        """
        self._error_handlers[code] = f

    def handle_exception(self, request, e, exc_info=None):
        """
        Handles an exception within the application.
        If a corresponding handler is registered with the application
        we call that otherwise a generic message is displayed.
        """
        from webob import exc
        if isinstance(e, exc.HTTPException):
            if isinstance(e, exc.HTTPServerError):
                logger.error('HTTP Server Error: "%s"' % e, exc_info=1)
            status = e.code 
        else:
            # If in debug mode show the debug error page.
            if self.config['DEBUG']:
                # Raise the error for the debugger.
                if exc_info[1] is e:
                    # If the exception is the original exception raise it.
                    # so the debugger shows the right traceback.
                    raise exc_info[0], exc_info[1], exc_info[2]
                else:
                    # The exception passed is different from the exc_info
                    # so just re-raise it.
                    raise e
            
            # Otherwise return a normal HttpInternalServerError
            logger.error('Internal Server Error: "%s"' % e, exc_info=1)
            status = 500
            e = exc.HTTPInternalServerError()
        
        handler = self._error_handlers.get(status)
        if handler:
            return self.make_response(request, handler(e))
        else:
            return self.make_response(request, e)

    def make_response(self, request, rv, after_request_funcs=True):
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

        if after_request_funcs:
            after_rv = None
            for func in reversed(self._after_request_funcs):
                after_rv = func(request, rv)
                if after_rv:
                    return self.make_response(request, after_rv, False)

        return rv
