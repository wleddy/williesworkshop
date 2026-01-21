from flask import request, session, g, redirect, url_for, \
     render_template, flash, Blueprint
import json
from datetime import datetime, time
from shotglass2.takeabeltof.date_utils import local_datetime_now
from shotglass2.takeabeltof.utils import printException, cleanRecordID, is_mobile_device
from shotglass2.users.admin import login_required, table_access_required
from shotglass2.takeabeltof.views import TableView, EditView
from shotglass2.takeabeltof.jinja_filters import plural

import light_control.models as models


PRIMARY_TABLE = models.LightControl

mod = Blueprint('lights',__name__, 
                template_folder='templates/light_control/', 
                static_folder='static/',
                url_prefix='/lights',
                )


def setExits():
    g.listURL = url_for('.display')
    g.editURL = url_for('.edit')
    g.deleteURL = url_for('.display') + 'delete/'
    g.title = f'{plural(PRIMARY_TABLE(g.db).display_name,2)}'


# this handles table list and record delete
@mod.route('/<path:path>',methods=['GET','POST',])
@mod.route('/<path:path>/',methods=['GET','POST',])
@mod.route('/',methods=['GET','POST',])
@table_access_required(PRIMARY_TABLE)
def display(path=None):
    # import pdb;pdb.set_trace()
    setExits()
    
    view = TableView(PRIMARY_TABLE,g.db)
    # optionally specify the list fields
    # view.list_fields = [
    #     ]
    
    return view.dispatch_request()
    

## Edit the PRIMARY_TABLE
@mod.route('/edit', methods=['POST', 'GET'])
@mod.route('/edit/', methods=['POST', 'GET'])
@mod.route('/edit/<int:rec_id>/', methods=['POST','GET'])
@table_access_required(PRIMARY_TABLE)
def edit(rec_id=None):
    setExits()
    print(PRIMARY_TABLE(g.db).display_name)
    g.title = "Edit {} Record".format(PRIMARY_TABLE(g.db).display_name)

    view = EditView(PRIMARY_TABLE,g.db,rec_id)
    # Optonally may want to specify the edit fields to use with default edit form
    # otherwise all fields will be included except forgien keys

    # view.edit_fields = []
    
    # view.edit_fields.extend(
    #     [
    #     {'name':'location_name','req':True,},
    #     {'name':'entry_type','req':True,'type':'select','options':[
    #         {'name':'Departure'},
    #         {'name':'Point of Interest'},
    #         {'name':'Arrival'},
    #     ]},
    #     {'name':'entry_date','req':True,'type':'datetime','label':'When'},
    #     ]
    # )
    # entry_date_dict = {'name':'entry_date','type':'raw','content':''}
    # entry_date_dict['content'] = """<p><strong>Some Raw HTML</strong></p>"""
    # view.edit_fields.extend([entry_date_dict])

    # Some methods in view you can override
    # view.validate_form = validate_form # view does almost no validation
    # view.after_get_hook = ? # view has just loaded the record from disk
    # view.before_commit_hook = ? # view is about to commit the record

    # if is_mobile_device():
    #     # Sometimes not as convenient on mobile...
    #     view.use_anytime_date_picker = False


    # Process the form?
    if request.form:
        view.update(save_after_update=True)
        if view.success:
            return redirect(g.listURL)

    # otherwise send the list...
    return view.render()

    
def validate_form(view):
    # Validate the form
    valid_form = True
    view._set_edit_fields()
    for field in view.edit_fields:
        if field['name'] in request.form and field['req']:
            val = view.rec.__getattribute__(field['name'])
            if isinstance(val,str):
                val = val.strip()
            if not val:
                view.result_text = "You must enter a value for {}".format(field['name'])
                flash(view.result_text)
                view.success = False
                valid_form = False
            
    return valid_form

    
def create_menus():
    """
    Create menu items for this module

    g.menu_items and g.admin are created in app.

    Menu elements defined directly in menu_items have no access control.
    Menu elements defined using g.admin.register can have access control.

    """

    # # Static dropdown menu...
    # g.menu_items.append({'title':'Drop down header','drop_down_menu':{
    #         'name':'First','url':url_for('.something'),
    #         'name':'Second','url':url_for('.another'),
    #         }
    #     })
    # # single line menu
    # g.menu_items.append({'title':'Something','url':url_for('.something')})
    
    # This makes a drop down menu for this application
    g.admin.register(PRIMARY_TABLE,url_for('.display'),display_name='Lights',header_row=True,minimum_rank_required=500,roles=['admin',])
    g.admin.register(PRIMARY_TABLE,
        url_for('.display'),
        display_name=plural(PRIMARY_TABLE(g.db).display_name,2),
        top_level=False,
        minimum_rank_required=500,
    )

def register_blueprints(app, subdomain = None) -> None:
    """
    Register one or more modules with the Flask app

    Arguments:
        app -- the current app

    Keyword Arguments:
        subdomain -- limit access to this subdomain if difined (default: {None})
    """ 
    app.register_blueprint(mod, subdomain=subdomain)


def initialize_tables(db) -> None:
    """
    Initialize all the tables for this module

    Arguments:
        db -- connection to the database
    """
    
    models.init_db(db)