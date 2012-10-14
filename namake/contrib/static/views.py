import os

def send_static_file(request, filename):
    """Function used internally to send static files from the static
    folder to the browser.
    """
    from .helpers import send_from_directory

    static_folder = request.app.config.get('STATIC_FOLDER')
    if not static_folder:
        raise RuntimeError('No static folder for this object')
    # Ensure get_send_file_max_age is called in all cases.
    cache_timeout = request.app.static_files.get_send_file_max_age(filename)
    return send_from_directory(request,
                       os.path.join(request.app.root_path, static_folder), filename,
                       cache_timeout=cache_timeout)
