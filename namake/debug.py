"""
Helpers for development/debugging handling.
"""

from string import Template

from webob.exc import HTTPInternalServerError

class DebugHTTPInternalServerError(HTTPInternalServerError):
    body_template_obj = Template('''\
${explanation}<br /><br />
${detail}
<h2>Traceback</h2>
${traceback}
<h2>Headers</h2>
${headers}
<h2>WSGI Environment</h2>
${environ}
''')

    def __init__(self, *args, **kwargs):
        self.exc_info = kwargs.pop('exc_info', None)
        super(DebugHTTPInternalServerError, self).__init__(*args, **kwargs)

    def html_body(self, environ):
        from webob import html_escape
        import traceback

        args = {
            'explanation': html_escape(self.explanation),
            'detail': html_escape(self.detail or ''),
            'comment': html_escape(self.comment or ''),
        }
        if self.exc_info:
            args['traceback'] = '<br />'.join(traceback.format_exception(self.exc_info[0],
                self.exc_info[1], self.exc_info[2]))
        else:
            args['traceback'] = ''

        # Custom template; add headers to args
        args['environ'] = '<br />'.join(['%s=%s' % (html_escape(k),html_escape(v)) for k,v in environ.items()])
        args['headers'] = '<br />'.join(['%s=%s' % (html_escape(k.lower()),html_escape(v)) for k,v in self.headers.items()])

        return self.html_template_obj.substitute(
            status=self.status,
            body=self.body_template_obj.substitute(args),
        )
