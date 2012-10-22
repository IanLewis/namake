namake
======

A lazy-loaded WebOb based WSGI micro-framework.

Motivation
--------------------------

Many frameworks make the assumption that all application code is loaded at
startup time, thus making requests after startup faster.

However, for some applications, particularly those on Google Appengine, this
can be problematic due to the fact that startup requires access to a lot of
files on disk and perform lots of startup tasks before it can start serving
requests. This can be an anathema to environments where scaling is required
as server processes can be can started and killed fairly often.

In order to build an application that allows smoother transition for servers
that are being started and killed often namake itself lazy loads as much as
possible as well as encouraging applications to do so as well. Apps that
require modules to be loaded at startup can still load them at startup
in their own application code.

Namake is a micro-framework so the framework core will remain very small and won't
make many assumptions about the environment that you are using besides the webob
library. Extra functionality, such as for the App Engine environment or for for
Jinja2 templating, and sessions will be contained in contrib and extension modules.

Target Environments
--------------------------

The main target environment is Google App Engine so there was a conscious decision
to use Python versions and libraries that are readily available on App Engine.
It is for this reason that namake supports older verions of libraries like WebOb 1.1.1 and Jinja2 2.6.

However, namake can be used in any environment that has as WSGI server container,
so other envionments such as AWS Beanstalk or Heroku are also targets.

Requirements
--------------------------

Currently the namake core has the following requirements:

    Python >= 2.7
    WebOb >= 1.1.1

For Jinja2 templating:

    Jinja2 >= 2.6

For the local development server (not required in production):

    Werkzeug >= 0.8.3

Current Status
--------------------------

namake is currently just an experiment so the code is by definition experimental.
Depending on how well the ideas work out, it may be developed into a full usable
framework. However, currently you are not recommended to use the code in
a production environment.


Getting Started
--------------------------

If you would like to try it out you can get started by cloning the project
from github and installing it in a virtualenv.

    $ git clone git://github.com/IanLewis/namake.git
    ...
    $ cd namake
    $ pip install -e . -E /path/to/venv

You can create a sample python app pretty simply. All views/controllers are 
callables that take the request as a first parameter and regex arguments as
subsequent parameters:

    from namake import Application, Response
    app = Application()
    app.add_route('/', lambda request: Response("Hello World"))
    if __name__ == '__main__':
        from namake.contrib.devserver import run_devserver
        run_devserver(app)

You can run it from the command line like so. Sorry, no HTML tracebacks or interactive debugging.

    $ python myapp.py
     * Running on http://localhost:8000/
     * Restarting with reloader

Accessing http://localhost:8000/ should produce the Hello World text.

To use namake's lazy loading, you need to specify the import path to the controller
rather than a reference to the controller itself.

    app.add_route('/', 'path.to.my.controller')
