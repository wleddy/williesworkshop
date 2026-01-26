# Rui Santos & Sara Santos - Random Nerd Tutorials
# Complete project details at https://RandomNerdTutorials.com/raspberry-pi-pico-w-asynchronous-web-server-micropython/

# Import necessary modules
import network
import uasyncio as asyncio
import socket
import time
import random
import sys
import json
from machine import Pin
from logging import logging as log
from ntp_clock import Clock
from machine import RTC
from wifi_connect import connection
from os_path import make_path

# log.setLevel(log.DEBUG)

if sys.platform == 'esp32':
    led = Pin(2, Pin.OUT)
else:
    led = Pin('LED', Pin.OUT)
    
relay_pin = Pin(2, Pin.OUT)
relay_pin.off()

connection.connect()

rtc = Clock()
try:
    rtc.set_time()
except:
    pass

DATA_FILE = "instance/lights.json"


def acknowledge(times=3):
    led.on()
    for x in range(times):
        time.sleep(0.5)
        led.toggle()
    
acknowledge()

async def manage_switch():
    if not connection.is_connected():
        connection.connect()
    if not rtc.has_time:
        rtc.set_time()
    try:
        the_time = rtc.time_string(format=24)
        if the_time == '--:--':
            the_time = None
    except:
        the_time = None
        
    data = json.loads(get_status_from_file())
    timer_on = False
    light_on = False
    new_mode = data.get('mode',-1)

    if the_time:
        
        if 'timers' in data and the_time:
            for timer in data['timers']:
#                 print('the time:',the_time,'start:',timer[0],'end time:',timer[1])
                if timer[0] <= the_time and timer[1] >= the_time:
                    timer_on = True
                    break
        state = data.get('mode',-1)
        if state == -1 and timer_on: #auto
            light_on = True
        elif state == 0: #Always off
            light_on = False
        elif state == 1: #Always On
            light_on = True
        elif state == 2 and timer_on: #on till next
            light_on = True
            new_mode = -1 # set back to auto
        elif state == 2 and not timer_on: #on till next
            light_on = True
        elif state == 3 and timer_on: #Off till next
            light_on = False
        elif state == 3 and not timer_on:
            light_on = False
            new_mode = -1 #set back to auto
        
        if light_on:
            led.on()
            relay_pin.on()
        else:
            led.off()
            relay_pin.off()
    else:
        # Don't have the time...
        led.off()
        relay_pin.off()
        
    # save the data?
    if new_mode != data.get('mode'):
        print('saving:',data)
        save_status_to_file(json.dumps(data))
        

def save_status_to_file(data):
    make_path('/',DATA_FILE)
    with open(DATA_FILE,'w') as f:
            f.write(data)

def get_status_from_file():
    default_content = '{"mode":-1,delay_seconds":10, "timers":[["17:00","22:00"]]}' # default value
    content = ''
    try:
        with open(DATA_FILE,"r") as f:
            content = f.read()
    except:
        pass
    
    if not content:
        content = default_content
        print("using default data")

    return content

def decode(data):
    # decode json text 
    data = data.replace('%7B','{')
    data = data.replace('%7D','}')
    data = data.replace('%22','"')
    data = data.replace('%3A',':')
    data = data.replace('+',' ')
    data = data.replace('%2C',',')
    data = data.replace('%5B','[')
    data = data.replace('%5D',']')
    data = data.replace('%20',' ')
    return data

def status():
    acknowledge(1)
    content = get_status_from_file()
    print(f"handle status request: {content}")

    return content

def update(data):
    acknowledge(1)
    if data:        
        save_status_to_file(data)
        content = 'Ok'
    else:
        content = "No Data here"
    content = 'Ok'
    print(f"update request returned: {content}")
    
    return content


# Asynchronous functio to handle client's requests
async def handle_client(reader, writer):
    
    print("Client connected")
    request_line = await reader.readline()
    print('Request:', request_line)
    
    # Skip HTTP request headers
    while await reader.readline() != b"\r\n":
        pass
    
    request = str(request_line, 'utf-8').split()[1]
#     print('Request:', request)
    
    if request == '/lights/status.json':
        response = status()
    elif request.startswith('/lights/update?'):
        data = ''
        tmp = request.split('?')
        if len(tmp) > 1:
            data = decode(tmp[1])
            print('data received: '+ data)

        response = update(data)
    else:
        response = ''
        
    if response:
        # Send the HTTP response and close the connection
        writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        writer.write(response)
        await writer.drain()
    else:
        writer.write('HTTP/1.0 404 NOT FOUND\r\nContent-type: text/html\r\n\r\n')
        writer.write('Page Not Found')
        await writer.drain()
        
    await writer.wait_closed()
    print('Client Disconnected')
    

async def main():    
    if not connection.is_connected():
        connection.connect()
    if not rtc.has_time:
        rtc.set_time()
    
    # Start the server and run the event loop
    print('Setting up server')
    server = asyncio.start_server(handle_client, "0.0.0.0", 80)
    asyncio.create_task(server)
    asyncio.create_task(manage_switch())
    
    while True:
        # Add other tasks that you might need to do in the loop
        await asyncio.sleep(1)
        await manage_switch()

# Create an Event Loop
loop = asyncio.get_event_loop()
# Create a task to run the main function
loop.create_task(main())

try:
    # Run the event loop indefinitely
    loop.run_forever()
except Exception as e:
    print('Error occurred: ', e)
except KeyboardInterrupt:
    print('Program Interrupted by the user')