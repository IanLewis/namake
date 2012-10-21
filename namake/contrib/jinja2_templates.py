from namake.utils.decorators import locked_cached_property

__all__ = (
    'Jinja2Mixin',
    'render_template',
    'render_template_string',
)

class Jinja2(object):
    """
    A mixin class for use with the Application
    class in order to set up a Jinja2 environment.
    """
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app, handle_errors=True):
        import os

        self.app = app
        app.jinja2 = self
        app.extensions['jinja2'] = self

        app.config.setdefault('JINJA2_TEMPLATE_DIRS', [os.path.join(app.root_path, 'templates')])
        app.config.setdefault('JINJA2_EXTENSIONS', ['jinja2.ext.autoescape', 'jinja2.ext.with_'])
        app.config.setdefault('JINJA2_AUTOESCAPE_FILE_EXTENSIONS', ['.html', '.htm', '.xml', '.xhtml'])

        if handle_errors:
            app.register_error_handler(404, self.handle_404)
            app.register_error_handler(500, self.handle_500)

    @locked_cached_property
    def env(self):
        if not hasattr(self, '_jinja2_env'):
            from jinja2 import FileSystemLoader, Environment
            
            extensions = self.app.config['JINJA2_EXTENSIONS']
            loader = FileSystemLoader(self.app.config['JINJA2_TEMPLATE_DIRS'])
            autoescape = self.select_jinja_autoescape

            self._jinja2_env = Environment(
                extensions=extensions,
                loader=loader,
                autoescape=autoescape,
            )
        return self._jinja2_env

    def select_jinja_autoescape(self, filename):
        """Returns `True` if autoescaping should be active for the given
        template name.

        .. versionadded:: 0.5
        """
        if filename is None:
            return False
        return filename.endswith(tuple(self.app.config['JINJA2_AUTOESCAPE_FILE_EXTENSIONS']))

    def update_template_context(self, context):
        pass


    def handle_404(self, e):
        """
        A 404 error handler which renders the template "404.html"
        as as response.
        """
        template = self.env.get_or_select_template("404.html")
        return template.render()

    def handle_500(self, e):
        """
        A 500 error handler which renders the template "500.html"
        as as response.
        """
        template = self.env.get_or_select_template("500.html")
        return template.render()

def render_template(request, template_name_or_list, context):
    request.app.jinja2.update_template_context(context)
    template = request.app.jinja2.env.get_or_select_template(template_name_or_list)
    return template.render(context)

def render_template_string(request, source, context):
    request.app.jinja2.update_template_context(context)
    template = request.app.jinja2.env.from_string(source)
    return template.render(context)
