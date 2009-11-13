While Django's development server is fine for trying Motion out, to run Motion
on a production internet web site requires a more stable Web server
environment. Because Django applications can run as [WSGI applications][wsgi],
you have several excellent options for production grade application serving.
We recommend using Apache with [mod\_wsgi][modwsgi].

[wsgi]: http://wsgi.org/wsgi/Learn_WSGI
[modwsgi]: http://code.google.com/p/modwsgi/

## Installing mod\_wsgi ##

Many Linux distributions provide Apache and mod\_wsgi as packages for easy
installation.

Once mod\_wsgi is installed, make sure Apache is configured to use it.
Somewhere in the Apache configuration will need to be a directive to load the
mod\_wsgi module. The `LoadModule` directive looks like this:

    LoadModule wsgi_module modules/mod_wsgi.so

If you installed mod\_wsgi from a package, though, it will probably have
already configured this. Consult the documentation for your mod\_wsgi package.

For further guidance, see [the mod\_wsgi installation guide][mw-inst].

[mw-inst]: http://code.google.com/p/modwsgi/wiki/InstallationInstructions

## Configuring Motion for mod\_wsgi ##

Once you've installed mod\_wsgi and [made a Motion project][motion-install],
you need only configure Apache to serve your Motion project as a WSGI
application.

[motion-install]: http://developer.typepad.com/motion/create-motion.html

### Your Motion and Typepadapp library paths ###

For some of the Apache configuration directives, you'll need to know where
your Motion and Typepadapp *library paths* are. That's where on the filesystem
the `motion` and `typepadapp` Python packages are installed. You can find out
your Motion path by running this command:

    python -c "import motion; print motion.__file__"

This should tell you a full path to the main `motion` Python file, such as:

    /usr/lib/python2.6/site-packages/typepad_motion-1.0.2-py2.6.egg/motion/__init__.pyc

The `__init__.pyc` at the end is the package filename, so ignore that part. In
this case, your Motion library path would be the first part:
`/usr/lib/python2.6/site-packages/typepad_motion-1.0.2-py2.6.egg/motion`. This
is the path we'll need to use in the Apache configuration directives.

Do the same with `typepadapp` instead of `motion` to get your Typepadapp
library path:

    python -c "import typepadapp; print typepadapp.__file__"

### Your site project path ###

We'll also need to configure Apache to point to [the Motion site you already
created][motion-install]. The `typepadproject` command you used to create a
Motion project created your site, including the settings files you configured
with your site's settings. We'll put a new file called `app.wsgi` in this
directory that will tell mod\_wsgi how to run your Motion site.

Because we'll need to use your project path in the Apache configuration,
you'll need to know the full path to your Motion project directory. To find
out what it is, at the terminal in the Motion project directory, enter:

    pwd

This command will show you a full path to your project, something like:

    /home/example/mymotion

This is the full project path we'll use to configure Apache.

### The `app.wsgi` file ###

We'll need a new file called `app.wsgi` in your site project path to tell
mod\_wsgi how to run your Motion site. Download this file to your site project
path (replacing the existing the `app.wsgi` file if one is already there):

[Download app.wsgi](http://developer.typepad.com/motion/app.wsgi)

Once that file is there, we need only configure Apache to run a mod\_wsgi site
using those file's directions.

### The Apache configuration ###

Here's the Apache configuration we recommend for running Motion under
mod\_wsgi. This example configuration sets up Motion to run with these
settings:

* Domain name: `motion.example.com`
* Motion library path: `/MOTION/PATH`
* Typepadapp library path: `/TYPEPADAPP/PATH`
* Project path: `/PROJECT/PATH`

When using this configuration, make sure to replace the paths with your own as
you found above.

    <VirtualHost *:80>
        ServerName motion.example.com

        # serve static files directly through apache
        Alias /static/themes/motion /MOTION/PATH/static/theme
        Alias /static/motion /MOTION/PATH/static
        Alias /static/typepadapp /TYPEPADAPP/PATH/static

        # serve motion with mod_wsgi
        WSGIScriptAlias / /PROJECT/PATH/app.wsgi
        WSGIProcessGroup motionsites
        WSGIDaemonProcess motionsites display-name=%{GROUP} processes=10 threads=1
    </VirtualHost>

By using [a `<VirtualHost>` section][apache-vhost] like this, the Motion site
would run on its own domain, `motion.example.com`. If you're adding the Motion
application to an existing site, you may wish to add the individual directives
above into your existing Apache configuration, instead of putting them in a
new `<VirtualHost>` section. See [the Apache manual][apache-conf] for more
information about configuring Apache.

[apache-vhost]: http://httpd.apache.org/docs/2.0/vhosts/
[apache-conf]: http://httpd.apache.org/docs/2.0/

## Possible problems ##

There are a few issues to keep in mind when setting up Motion with mod\_wsgi.
If you run into other problems, please do [ask around][help] about it.

[help]: http://developer.typepad.com/help/

### Database configuration ###

While our initial developer configuration uses Django's default SQLite
database, when running a production site, you may want to use another database
such as MySQL. Consult the Django documentation for [how to install additional
database support][django-db] and [the settings to reconfigure your
project][django-dbconf] to use another database system.

If you want to continue using SQLite, you'll need to make sure the Apache user
has permission to write to the directory the database file is in, so it can
properly lock the database against simultaneous writes. Also, when specifying
your database file's name in the `DATABASE_NAME` setting, use the file's full
path; mod\_wsgi won't be able to find the database with only the path from
your project directory or a lone filename.

[django-db]: http://docs.djangoproject.com/en/dev/topics/install/#database-installation
[django-dbconf]: http://docs.djangoproject.com/en/dev/ref/settings/#setting-DATABASE_ENGINE

### UNIX socket paths ###

The above configuration sets up mod\_wsgi in *daemon mode*, which requires
that mod\_wsgi processes be able to read from UNIX sockets the Apache
processes open. This normally works fine, but some Linux distributions may put
more restrictive permissions on Apache's default socket path, resulting in
"503 Service Temporarily Unavailable" responses and a "Permission denied"
error in the Apache error log. See [the mod\_wsgi documentation][modwsgi-sox]
for more information on configuring your socket path.

[modwsgi-sox]: http://code.google.com/p/modwsgi/wiki/ConfigurationIssues#Location_Of_UNIX_Sockets

### Python egg cache path ###

Using daemon mode also means the mod\_wsgi processes may need to write to the
Python egg cache. This path is used to unpack zipped eggs for use; you may
have installed (such as when using `pip` instead of `easy_install`), in which
case no additional configuration is necessary. If you receive an
"ExtractionError" and a message about the Python egg cache in your Apache
error log, check the permissions on the directory or reconfigure the egg cache
path [as described in the mod_wsgi documentation][modwsgi-eggs].

[modwsgi-eggs]: http://code.google.com/p/modwsgi/wiki/ApplicationIssues#Access_Rights_Of_Apache_User

### Setting User and Group before configuring WSGI ###

The daemon mode configuration depends on the `User` and `Group` settings in
the Apache configuration being set before the `WSGIDaemonProcess` directive.
Some Linux distributions' default may include before the `User` and `Group`
directives. If you get an `Unable to determine home directory for uid` error
in the Apache error log, check that the Apache configuration is setting `User`
and `Group` before it gets to the Motion configuration block you added above.

### SELinux ###

Daemon mode can also be more complicated to configure under SELinux. You might
find it easier to use *embedded mode* instead. You can see [more about SELinux
in the mod\_wsgi documentation][modwsgi-selinux].

[modwsgi-selinux]: http://code.google.com/p/modwsgi/wiki/ApplicationIssues#Secure_Variants_Of_UNIX

### Virtual environments ###

This guide covers running Motion from the regular Python library path. If
you're configuring Motion to run from a Python virtual environment, see
[mod\_wsgi's excellent virtual environments documentation][modwsgi-venv].

[modwsgi-venv]: http://code.google.com/p/modwsgi/wiki/VirtualEnvironments

## Happy Motion ##

We hope this guide helps you run more public, stable Motion sites using
mod\_wsgi. If you have trouble or other tips for running production Motion
sites, please [let us and the community know][help].
