from flask import g, session, request, redirect, abort, url_for
import os
from shotglass2 import shotglass
from shotglass2.takeabeltof.database import Database
from shotglass2.takeabeltof.jinja_filters import register_jinja_filters
from shotglass2.tools.views import tools
from shotglass2.users.admin import Admin
from shotglass2.users.models import User

# Create app
import logging 

app = shotglass.create_app(
        __name__,
        instance_path='instance',
        config_filename='site_settings.py',
        static_folder=None,
        )
        
def start_app():
    shotglass.start_logging(app)
    initalize_base_tables()
    ## Setup the routes for users
    shotglass.register_users(app)

    # setup www.routes...
    shotglass.register_www(app)

    app.register_blueprint(tools.mod)
    
    register_blueprints() # Register all the other bluepints for the app

    # use os.path.normpath to resolve true path to data file when using '../' shorthand
    shotglass.start_backup_thread(
        os.path.normpath(
            os.path.join(
                app.root_path,shotglass.get_site_config()['DATABASE_PATH']
                )
            )
        )


@app.context_processor
def inject_site_config():
    # Add 'site_config' dict to template context
    return {'site_config':shotglass.get_site_config()}

register_jinja_filters(app)


def get_db(filespec=None):
    """Return a connection to the database.

    If the db path does not exist, create it and initialize the db"""

    if not filespec:
        filespec = shotglass.get_site_config()['DATABASE_PATH']

    # This is probobly a good place to change the
    # filespec if you want to use a different database
    # for the current request.

    # test the path, if not found, try to create it
    if shotglass.make_db_path(filespec):
        g.db = Database(filespec).connect()
        initalize_base_tables(g.db)
    
        return g.db
    else:
        # was unable to create a path to the database
        raise IOError("Unable to create path to () in app.get_db".format(filespec))

    
@app.context_processor
def inject_site_config():
    # Add 'site_config' dict to template context
    return {'site_config':shotglass.get_site_config()}


@app.before_request
def _before():
    # Force all connections to be secure
    if app.config['REQUIRE_SSL'] and not request.is_secure :
        return redirect(request.url.replace("http://", "https://"))

    #ensure that nothing is served from the instance directory
    if 'instance' in request.url:
        return abort(404)
        
    # import pdb;pdb.set_trace()
    # print(app.url_map)
    session.permanent = True
    
    shotglass.get_site_config(app)
    shotglass.set_template_dirs(app)
    
    get_db()
    
    # Is the user signed in?
    g.user = None
    if 'user' in session:
        g.user = session['user']
        
    create_menus()
        
        
def create_menus():
    """Create g.menu_items and g.admin objects.
    
    g.menu_items is a list of dicts that define the unprotected menu items. 
    They will be displayed to all visitors at the top (or left) of the menus.
    
    g.admin defines menu items that require a user logged in with at certain level
    of privilege.
    
    The order in which they are defined is the order in which they are displayed.
    """
    # g.menu_items should be a list of dicts
    #  with keys of 'title' & 'url' used to construct
    #  the non-table based items in the main menu
    g.menu_items = [
        {'title':'Home','url':url_for('www.home')},
        {'title':'Contact Me','url':url_for('www.contact')},
        ]
        
    # g.admin items are added to the navigation menu by default
    g.admin = Admin(g.db) # This is where user access rules are stored
    
    # # Add a module to the menu
    # g.admin.register(Starter,
    #         url_for('starter.display'),
    #         display_name='Starter',
    #         top_level=True,
    #         minimum_rank_required=500,
    #     )
    
    # This one will set up the view log item
    g.admin.register(User,
            url_for('tools.view_log'),
            display_name='View Log',
            top_level = True,
            minimum_rank_required=500,
        )
    
    
    shotglass.user_setup() # g.admin now holds access rules Users, Prefs and Roles

@app.teardown_request
def _teardown(exception):
    if 'db' in g:
        g.db.close()


@app.errorhandler(404)
def page_not_found(error):
    return shotglass.page_not_found(error)

@app.errorhandler(500)
def server_error(error):
    return shotglass.server_error(error)


def initalize_base_tables(db=None):
    """Place code here as needed to initialze all the tables for this site"""
    if not db:
        db = get_db()
    
    shotglass.initalize_user_tables(db)

    # ### setup any other tables you need here....
    # import starter_module.models
    # starter_module.models.init_db(db)
    
def register_blueprints():
    """Register all your blueprints here and initialize 
    any data tables they need.
    """
    # # add app specific modules...
    # from starter_module.models import init_db as starter_init
    # starter_init(g.db) #initialize the tables for the module
    # from starter_module.views import starter
    # app.register_blueprint(starter.mod)
    # # update function 'create_menus' to display menu items for the app


#Register the static route
app.add_url_rule('/static/<path:filename>','static',shotglass.static)

# To use a different subdomain as asset server, use this instead
# Direct to a specific server for static content
#app.add_url_rule('/static/<path:filename>','static',shotglass.static,subdomain="somesubdomain")


with app.app_context():
    start_app()


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
    #app.run()
    
    