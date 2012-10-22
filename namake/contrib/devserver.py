import os
import argparse

from werkzeug.serving import run_simple

__all__ = ('run_devserver',)

def run_devserver(app):
    """
    Run a reloading development server.
    """
    parser = argparse.ArgumentParser(
        description="""The Namake Development Server."""
                    """The server can serve static files automatically """
                    """and reload when code files are updated."""
    )
    parser.add_argument('-H', '--hostname', dest="hostname", default='localhost',
                       help="The hostname to bind the server to.")
    parser.add_argument('-p', '--port', dest="port", default='8000', type=int,
                       help="The port to use for the server.")
    parser.add_argument('--nostatic', dest="static", action='store_false', default=True,
                       help="Don't serve static files.")
    parser.add_argument('--noreload', dest="reload", action='store_false', default=True,
                       help="Don't reload code when the files are updated.")
    parser.add_argument('--nodebugger', dest="debugger", action='store_false', default=True,
                       help="Don't show debug responses when errors occur.")

    config = parser.parse_args()
    
    app.config.setdefault('STATIC_FOLDER', 'static')
    static_folder = app.config['STATIC_FOLDER']

    run_simple(
        hostname=config.hostname, 
        port=config.port,
        application=app,
        use_reloader=config.reload,
        use_debugger=config.debugger,
        static_files={
            '/%s' % static_folder: os.path.join(app.root_path, static_folder) 
        } if config.static else None
    )
