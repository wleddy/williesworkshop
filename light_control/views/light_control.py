from flask import request, session, g, redirect, url_for, \
     render_template, flash, Blueprint
import json
import time
from os import path
import requests
import urllib3
from shotglass2.takeabeltof.date_utils import local_datetime_now, datetime_as_string
from shotglass2.takeabeltof.utils import printException, cleanRecordID, is_mobile_device
from shotglass2.users.admin import login_required, table_access_required
from shotglass2.takeabeltof.views import TableView, EditView
from shotglass2.takeabeltof.jinja_filters import plural

import light_control.models as models


PRIMARY_TABLE = models.LightControl
URL_PREFIX = 'lights'
TESTING_DATA = 'instance/light_control.json'

mod = Blueprint('lights',__name__, 
                template_folder='templates/light_control/', 
                static_folder='static/',
                url_prefix=f'/{URL_PREFIX}',
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

@mod.route('get/<uuid>',methods=['GET','POST',])
@mod.route('get/<uuid>/',methods=['GET','POST',])
@mod.route('get/',methods=['GET','POST'])
@mod.route('get',methods=['GET','POST'])
@table_access_required(PRIMARY_TABLE)
def get(uuid = None):
    """ Retrieve or set the settings for a light controler
    
    Use the uuid to retieve the light_control record and return a JSON text string with current settings
    If a POST update the controler data
    
    Args: uuid: str | None;
    
    Returns:  str
    
    Raises: None
    """
    g.listURL = url_for('.get')
    g.editURL = url_for('.get')
    g.cancelURL = g.listURL
    g.title = "Light Controller"

    urllib3.disable_warnings() # disable the security warning


    #### For testing
    def encrypt(data):
        return data
    def decrypt(data,*args,**kwargs):
        return data
    

    def _validate_post(form):
        # validate and organize the post data
        # get all the timer fields first
        def handle_timer():
            if start_tag in form and end_tag in form:
                if form[start_tag] and form[end_tag]: # if either is empty don't record but continue outer loop
                    timers.append([form[start_tag],form[end_tag]])
                return True
            else:
                return False

        timers = []
        for x in range(1,11): # I dont expect more than 10 timers
            start_tag = f"timer_{x}_on"
            end_tag = f"timer_{x}_off"
            if not handle_timer(): break
        start_tag = 'new_timer_on'
        end_tag = 'new_timer_off'
        handle_timer()
        timers.sort()
        data['timers'] = timers

        # get the rest of the elements
        for k,v in form.items():
            if k == 'name' and v:
                data[k] = v # name may not be empty
            elif k in ['uuid',"secret","host"]:
                pass # never update these
            elif 'timer' in k:
                pass # already handled above
            else:
                data[k] = v


    # import pdb;pdb.set_trace()

    data = {"error":'',}

    if not uuid:
        uuid = request.form.get('uuid')

    if not uuid:
        recs = PRIMARY_TABLE(g.db).select()
        return render_template('lights_list.html',recs=recs)
    
    rec = PRIMARY_TABLE(g.db).select_one(where=f"uuid = {uuid}")
    if not rec:
        data['error'] = "That Device does not exist"
    else:
        try:
            data['date'] = datetime_as_string(local_datetime_now())
            if request.form:
                # validate data_dict then...
                _validate_post(request.form) # validated form is now in data
                rec.update(data)
                rec.save(commit=True)
                data['uuid'] = rec.uuid
                # some items must be int
                for k in ['state','delay_seconds']:
                    if k in data and isinstance(data[k],str):
                        try:
                            data[k] = int(data[k])
                        except:
                            pass

                data.update(data)
                # Send the new dict back to the device

                 #### for testing
                if 'williesworkshop' not in request.host:
                    rec.host = 'http://127.0.0.1:5000'

                # Encrypt data
                secret_data = encrypt(data)
                resp = requests.post(path.join(rec.host,URL_PREFIX,'update'),json=secret_data)
            else:
                 #### for testing
                if 'williesworkshop' not in request.host:
                    rec.host = 'http://127.0.0.1:5000'

                # ping host for current device state
                resp = requests.get(path.join(rec.host,URL_PREFIX,'status.json'))
                if resp and resp.status_code == 200:
                    if resp.text:
                        ct = decrypt(resp.text)
                        data = json.loads(ct)
                else:
                    raise ValueError(f"Not able to connect to device. resp.status: {resp.status_code} ")

            data['rec'] = rec
        except Exception as e:
            data['error'] = f'Error: Not able to load data. ({str(e)})'
    
    return render_template('lights_home.html',data=data)


### these two functions are going to live on the remote device
### Here just for testing
@mod.route('status.json',methods=['GET',])
def status():
    # import pdb;pdb.set_trace()
    try:
        with open(TESTING_DATA,'r') as f:
            return f.read()
    except FileNotFoundError:
        return ""

@mod.route('update',methods=['POST',])
def update():
    # import pdb;pdb.set_trace()
    if request.json:
        with open(TESTING_DATA,'w') as f:
            f.write(json.dumps(request.json))
    return 'ok'


def create_menus():
    """
    Create menu items for this module

    g.menu_items and g.admin are created in app.

    Menu elements defined directly in menu_items have no access control.
    Menu elements defined using g.admin.register can have access control.

    """

    # This makes a drop down menu for this application
    g.admin.register(PRIMARY_TABLE,url_for(f'{URL_PREFIX}.display'),display_name=URL_PREFIX.title(),header_row=True,minimum_rank_required=500,roles=['admin',])
    g.admin.register(PRIMARY_TABLE,
        url_for(f'{URL_PREFIX}.display'),
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