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
    def __init__(self, app):
        import os

        self.app = app
        app.jinja2 = self

        app.config.setdefault('JINJA2_TEMPLATE_DIRS', [os.path.join(app.root_path, 'templates')])
        app.config.setdefault('JINJA2_EXTENSIONS', ['jinja2.ext.autoescape', 'jinja2.ext.with_'])
        app.config.setdefault('JINJA2_AUTOESCAPE_FILE_EXTENSIONS', ['.html', '.htm', '.xml', '.xhtml'])

    @property
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


def render_template(request, template_name_or_list, context):
    request.app.jinja2.update_template_context(context)
    template = request.app.jinja2.env.get_or_select_template(template_name_or_list)
    return template.render(context)

def render_template_string(request, source, context):
    request.app.jinja2.update_template_context(context)
    template = request.app.jinja2.env.from_string(source)
    return template.render(context)
