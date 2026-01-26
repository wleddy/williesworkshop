# Rui Santos & Sara Santos - Random Nerd Tutorials
# Complete project details at https://RandomNerdTutorials.com/raspberry-pi-pico-w-asynchronous-web-server-micropython/

# Import necessary modules
import network
import uasyncio as asyncio
import socket
import time
import random
import json
from machine import Pin
from logging import logging as log
from ntp_clock import Clock
from machine import RTC
from wifi_connect import connection

log.setLevel(log.DEBUG)

# Wi-Fi credentials
ssid = 'Wallace'
password = '9164442903'


led = Pin('LED', Pin.OUT)

connection.connect()

rtc = Clock()
try:
    rtc.set_time()
except:
    pass

DATA_FILE = "instance/lights.json"

def aknowledge(times=3):
#     led.on()
    for x in range(times):
        time.sleep(0.5)
#         led.toggle()
    
aknowledge()

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
#     print(the_time)
#     print("from file...", get_status_from_file())
    if the_time:
        data = json.loads(get_status_from_file())
        timer_on = False
        light_on = False
        new_state = data.get('state',-1)
        if 'timers' in data and the_time:
            for timer in data['timers']:
                print('the time:',the_time,'start:',timer[0],'end time:',timer[1])
                if timer[0] <= the_time and timer[1] >= the_time:
                    timer_on = True
                    break
        state = data.get('state',-1)
        if state == -1 and timer_on: #auto
            light_on = True
        elif state == 0: #Always off
            light_on = False
        elif state == 1: #Always On
            light_on = True
        elif state == 2 and timer_on: #on till next
            light_on = True
            new_state = -1 # set back to auto
        elif state == 2 and not timer_on: #on till next
            light_on = True
        elif state == 3 and timer_on: #Off till next
            light_on = False
        elif state == 3 and not timer_on:
            light_on = False
            new_state = -1 #set back to auto
        
        # save the data?
        if new_state != data.get('state'):
            save_status_to_file(json.dumps(data))
        print("light is on?",light_on)
        if light_on:
            led.on()
        else:
            led.off()
    else:
        # Don't have the time...
        led.off()
        
    
def save_status_to_file(data):
    with open(DATA_FILE,'w') as f:
            f.write(data)

def get_status_from_file():
    default_content = '{"state":-1,"delay_seconds":10, "timers":[["17:00","22:00"]]}' # default value
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
    aknowledge(1)
    content = get_status_from_file()
    print(f"handle status request: {content}")

    return content

def update(data):
    aknowledge(1)
    if data:        
        save_status_to_file(data)
        content = 'Ok'
    else:
        content = "No Data here"
    content = 'Ok'
    print(f"update request returned: {content}")
    
    return content


# Init Wi-Fi Interface
def init_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    # Connect to your network
    wlan.connect(ssid, password)
    # Wait for Wi-Fi connection
    connection_timeout = 10
    while connection_timeout > 0:
        print(wlan.status())
        if wlan.status() >= 3:
            break
        connection_timeout -= 1
        print('Waiting for Wi-Fi connection...')
        time.sleep(1)
    # Check if connection is successful
    if wlan.status() != 3:
        print('Failed to connect to Wi-Fi')
        return False
    else:
        print('Connection successful!')
        network_info = wlan.ifconfig()
        print('IP address:', network_info[0])
        return True

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