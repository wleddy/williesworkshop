# Based on Rui Santos & Sara Santos - Random Nerd Tutorials
# Complete project details at https://RandomNerdTutorials.com/raspberry-pi-pico-w-asynchronous-web-server-micropython/

import asyncio
import time
import json
from machine import Pin
from ntp_clock import Clock
from wifi_connect import connection
from os_path import make_path
from logging import logging as log

led = Pin(26, Pin.OUT)
led.off()
on_board_led = Pin('LED',Pin.OUT)
    
relay_pin = Pin(10, Pin.OUT) # was 15 ... 15 may be toasted?
log.debug(f'Startup relay_pin: {relay_pin.value()}')
relay_pin.off()
push_button = Pin(14,Pin.IN,Pin.PULL_UP)

connection.connect()

rtc = Clock()
try:
    rtc.set_time()
except:
    pass

DATA_FILE = "instance/lights.json"

## Some Globals...
delay_time = -1
blink_delay = 0.5
blink_times = 0
button_buffer_ticks = time.ticks_ms()

def set_led(val):
    # keep the onboard and external leds in syinc
    led.value(val)
    on_board_led.value(val)


async def blink():
    global blink_times, blink_delay
    val = led.value()
    blink_times = int(blink_times)
    while blink_times > 0:
        for z in range(2):
            val = 1 if val == 0 else 0
            set_led(val)
            log.debug(f'Blink = Relay: {relay_pin.value()} LED: {led.value()}')
            await asyncio.sleep(blink_delay)
        blink_times -= 1
    set_led(relay_pin.value())
    # reset to defaults
    blink_delay = 0.5
    blink_times = 0


async def handle_button():
    global blink_times, blink_delay, button_buffer_ticks
    button_up = push_button.value()
    if button_up or button_buffer_ticks > time.ticks_ms():
        return # wait between button presses
    
    current_state = button_up
    light_on = (relay_pin.value() == 1)
    time.sleep(0.05)
    button_up = push_button.value()
    log.debug(f'Relay: {relay_pin.value()} LED: {led.value()} Light_on: {light_on}')
    if not button_up and button_up == current_state:
        print('button pressed')
        data = json.loads(get_status_from_file())
        val = 0 if led.value() == 1 else 1
        set_led(val)

        if light_on:
            data['mode'] = 3 # off till next
        else:
            data['mode'] = 2 # on till next
         
        # used to delay a bit before processing another press
        button_buffer_ticks = time.ticks_ms() + 2000

        # save the new status
        log.info(f'Button pressed, Mode: {data["mode"]}')
        save_status_to_file(json.dumps(data))
        

async def manage_mode():
    global delay_time, blink_delay, blink_times, relay_pin
    try:
        if not connection.is_connected():
            connection.connect()
        if not rtc.has_time:
            rtc.set_time()
        the_time = rtc.time_string(format=24)
        if the_time == '--:--':
            the_time = None
    except:
        the_time = None
        
    data = json.loads(get_status_from_file())
    timer_on = False
    light_on = False
    new_mode = data.get('mode',-1)

    if 'timers' in data and the_time:
        for timer in data['timers']:
            if timer[0] <= the_time and timer[1] >= the_time:
                timer_on = True
                break

    state = data.get('mode',0) # turn off by default for safety
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
        delay_time = 0
        relay_pin.value(1)
        log.debug(f'manage_mode = (Turn on light) Relay: {relay_pin.value()}, light_on: {light_on}')
    else:
#         print('delay_time:',delay_time,'Time:',time.time())
        if delay_time == 0:
            delay_time = time.time() + data.get('delay_seconds',0)
    #       print('delay_time set to:',delay_time,'Time:',time.time())
            blink_delay = 1
            blink_times = data.get('delay_seconds',0)

        elif time.time() >= delay_time:
            relay_pin.off()
            
    # save the data?
    if new_mode != data.get('mode'):
        data['mode'] = new_mode
        log.info(f'saving: {data}')
        save_status_to_file(json.dumps(data))
        
    log.debug(f'manage_mode = Relay: {relay_pin.value()} LED: {led.value()} Light_on: {light_on}')

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
        log.info("using default data")

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
    global blink_times, blink_delay
    blink_times = 2
    content = get_status_from_file()
#     print(f"handle status request: {content}")

    return content

def update(data):
#     global blink_times, blink_delay
#     blink_times = 2

##### TODO #####
# This needs to be more robust to validate the data
###############################

    if data:        
        save_status_to_file(data)
        content = 'Ok'
    else:
        content = "No Data here"
    content = 'Ok'
#     print(f"update request returned: {content}")
    
    return content


# Asynchronous functio to handle client's requests
async def handle_client(reader, writer):
    
    print("Client connected")
    request_line = await reader.readline()
    
    # Skip HTTP request headers
    while await reader.readline() != b"\r\n":
        pass
    
    request = str(request_line, 'utf-8').split()[1]
    
    response = ''
    
    if request == '/lights/status.json':
        response = status()
    elif request.startswith('/lights/update?'):
        data = ''
        tmp = request.split('?')
        if len(tmp) > 1:
            try:
                data = decode(tmp[1])
                response = update(data)
            except:
                pass
        
    if response:
        # Send the HTTP response and close the connection
        writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    else:
        writer.write('HTTP/1.0 404 NOT FOUND\r\nContent-type: text/html\r\n\r\n')
        response = 'Page Not Found'
        
    writer.write(response)
    await writer.drain()

    await writer.wait_closed()
    print('Client Disconnected')
    

async def main():
    global blink_times
    if not connection.is_connected():
        connection.connect()
    if not rtc.has_time:
        rtc.set_time()
    
    # Start the server and run the event loop
    print('Setting up server')
    server = asyncio.start_server(handle_client, "0.0.0.0", 80)
    asyncio.create_task(server)
    asyncio.create_task(manage_mode())
    asyncio.create_task(handle_button())
    asyncio.create_task(blink())
    
    blink_times = 2
    
    while True:
        try:
            # Add other tasks that you might need to do in the loop
            await asyncio.sleep(1) # a delay is needed to give server some time to work
            await manage_mode()
            await blink()
            await handle_button()
        except Exception as e:
            log.error(f'Main loop error: {str(e)}')

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