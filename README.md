# Shotglass

This is designed as a starter Flask installation with a minimum of dependancies. In conjunction with the 'users' package from
my github account. Shotglass and users provide a very simple framework to start a Flask project with the ability to add and 
manage users and roles to control access to your app.

By default, the main program file is app.py. App.py expects there to be a python package called 'users' and out-of-the-box 
won't run without it.

The ['users'](https://github.com/wleddy/users) package is it's own repository on github. All of the database functionality (sqlite3) is in users so the first thing
you probably want to do is clone users into your new flask app. See "Instructions" below.

## Instructions 

A typical approach would be to:

* create a new empty github repo for your new project
* clone it into your development machine
* get the .zip of the shotglass repo (don't clone it. You're making a new project)
* copy the contents of the .zip into your new project directory
* cd into the directory and clone the 'users' repo into it
* ensure that .gitignore includes "/users"
* do an initial commit of your new project, but be sure NOT to include users
* in the terminal run `. setup_env` This will create the instance directory where your private
  stuff is stored and will try to create virtualenv directory 'env' and pip the requirements into it.  
  * See the note below about virtualenv and requirements.txt with A2 Hosting
* Assuming everything went Ok, run `. activate_env` to enter your virtual environment.
* Next, edit the file at `instance/site_settings.py` with all your secrets.
* run python app.py to start the dev server and create the initial database. (unless your on A2, see below)
    
## Special Instructions for A2 Hosting

A2 Hosting uses this `passenger` system to run python apps on their system. Use the following steps to install your app.

1. In the terminal, `git clone` the new app as the directory you want to use.
2. cd into the new directory and `git clone https://github.com/wleddy/users.git`
3. run `. setup_env` to create the instance directory. It will not actually create a virtualenv.
4. Go to the "Setup Python App" cpanel and create a new app.  
    * set the "App Directory" to the directory you just cloned.
    * set the "App URI" to the URI visitors will use to access the site.
    * Click "Setup" to create your virtualenv. The path to the new is displayed there.
5. Back at the terminal in your new directory type `nano instance/activate_env` use the new virtualenv path as: 
 
`

    #!/bin/bash

    echo 'activating env from instance'
    source /home/< your account name >/virtualenv/< path to your project >/<version>/bin/activate

`

6. Save it, exit and type `. activate_env` to enter the virtualenv.
7. Type `pip install -r requirements.txt`
8. Edit instance/site_settings.py to add all your secrets.
9. Edit the file `passenger_wsgi.py`. Delete all the default text and replace it with `from app import app as application`
10. From the terminal, run `python app.py` This will start the development web server but also creates the default 
database records and is a good way to check that 
everything is working. If all goes well, type control + c to quit the dev server.
11. Type `touch tmp/restart.txt` to restart the app. You need to do this every time you make a change to the app.
12. In the App URI directory, A2 creates a default robots.txt file. Delete that to use the system at `www.views.home.robots`

***Easy as 1-2-3*** plus 9

### Required packages:

* python 3.6
* Flask and it's default dependencies, of course
* Flask-mail
* mistuse for Markdown support
* pytest
