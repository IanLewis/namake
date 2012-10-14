"""
Helpers for development/debugging handling.
"""

import os
from string import Template

from webob.exc import HTTPInternalServerError

# TODO: Smaller customized bootstrap.
# http://twitter.github.com/bootstrap/customize.html
with open(os.path.join(os.path.dirname(__file__), 'bootstrap.min.css')) as bsfd:
    _bootstrap_css = bsfd.read()
with open(os.path.join(os.path.dirname(__file__), 'bootstrap-responsive.min.css')) as bsfd:
    _bootstrap_responsive_css = bsfd.read()
with open(os.path.join(os.path.dirname(__file__), 'prettify.css')) as bsfd:
    _prettify_css = bsfd.read()
with open(os.path.join(os.path.dirname(__file__), 'prettify.js')) as bsfd:
    _prettify_js = bsfd.read()

class DebugHTTPInternalServerError(HTTPInternalServerError):
    html_template_obj = Template('''\
<!DOCTYPE html>
<html>
<head>
<title>${status}</title>
<style type="text/css">%s</style>
<style type="text/css">%s</style>
<style type="text/css">%s</style>
<script type="text/javascript">%s</script>
<style type="text/css">
.table {table-layout:fixed;width:100%%;}
.table td {word-wrap:break-word;}
pre.prettyprint {padding:10px 15px;}
</style>
</head>
<body onload="prettyPrint()">
  <div class="container">
  <h1>${status}</h1>
  ${body}
  </div>
</body>
</html>''' % (
    _bootstrap_css, _bootstrap_responsive_css,
    _prettify_css, _prettify_js.replace("$", "$$"),
))

    body_template_obj = Template('''\
${explanation}<br /><br />
${detail}
<div class="container-fluid">
  <div class="row-fluid">
    <div class="span2">
      <ul class="nav nav-list">
        <li><a href="#traceback">Traceback</a></li>
        <li><a href="#headers">Request Headers</a></li>
        <li><a href="#environ">WSGI Environment</a></li>
      </ul>
    </div>
    <div class="span10">
      <section id="traceback">
        <h2>Traceback</h2>
        <pre class="prettyprint">${traceback}</pre>
      </section>
      <section id="headers">
        <h2>Request Headers</h2>
        <table class="table table-striped table-hover">
          <tbody>
          ${headers}
          </tbody>
        </table>
      </section>
      <section id="environ">
        <h2>WSGI Environment</h2>
        <table class="table table-striped table-hover">
          <tbody>
          ${environ}
          </tbody>
        </table>
      </section>
    </div>
  </div>
</div>''')

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
            args['traceback'] = html_escape(''.join(traceback.format_exception(self.exc_info[0],
                self.exc_info[1], self.exc_info[2])))
        else:
            args['traceback'] = ''

        # Custom template; add headers to args
        args['environ'] = ''.join(['<tr><td><strong>%s</strong></td><td>%s</td></tr>' % (html_escape(k),html_escape(v)) for k,v in environ.items()])
        args['headers'] = ''.join(['<tr><td><strong>%s</strong></td><td>%s</td></tr>' % (html_escape(k.lower()),html_escape(v)) for k,v in self.headers.items()])

        return self.html_template_obj.substitute(
            status=self.status,
            body=self.body_template_obj.substitute(args),
        )
