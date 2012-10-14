class StaticFiles(object):
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        app.static_files = self
        app.extensions['static_files'] = self

        app.config.setdefault('STATIC_FOLDER', 'static')
        app.config.setdefault('STATIC_FILE_MAX_AGE_DEFAULT', 12 * 60 * 60) # 12 hours

        app.add_route('/' + app.config['STATIC_FOLDER'] + '/(?P<filename>.*)$',
              'namake.contrib.static.views.send_static_file')

    def get_send_file_max_age(self, filename):
        """Provides default cache_timeout for the :func:`send_file` functions.

        By default, this function returns ``SEND_FILE_MAX_AGE_DEFAULT`` from
        the configuration of :data:`~flask.current_app`.

        Static file functions such as :func:`send_from_directory` use this
        function, and :func:`send_file` calls this function on
        :data:`~flask.current_app` when the given cache_timeout is `None`. If a
        cache_timeout is given in :func:`send_file`, that timeout is used;
        otherwise, this method is called.

        This allows subclasses to change the behavior when sending files based
        on the filename.  For example, to set the cache timeout for .js files
        to 60 seconds::

            class MyFlask(flask.Flask):
                def get_send_file_max_age(self, name):
                    if name.lower().endswith('.js'):
                        return 60
                    return flask.Flask.get_send_file_max_age(self, name)

        .. versionadded:: 0.9
        """
        return self.app.config['STATIC_FILE_MAX_AGE_DEFAULT']
