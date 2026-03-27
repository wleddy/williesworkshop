# Based on Rui Santos & Sara Santos - Random Nerd Tutorials
# Complete project details at https://RandomNerdTutorials.com/raspberry-pi-pico-w-asynchronous-web-server-micropython/

import asyncio
import time
import json
from machine import Pin, PWM, soft_reset
from ntp_clock import Clock
from wifi_connect import connection
from os_path import make_path
from logging import logging as log

# log.setLevel(log.DEBUG)

led = Pin(26, Pin.OUT)
led.off()
on_board_led = Pin('LED',Pin.OUT)
    
relay_pin = Pin(10, Pin.OUT) # was 15 ... 15 may be toasted?
log.debug(f'Startup relay_pin: {relay_pin.value()}')
relay_pin.off()
push_button = Pin(14,Pin.IN,Pin.PULL_UP)
push_button_led = PWM(12, freq=300, duty_u16=65536//4) # reduce the brightness of the button led

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
light_on = False

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
    global blink_times, blink_delay, button_buffer_ticks, light_on
    button_up = push_button.value()
    if button_up or button_buffer_ticks > time.ticks_ms():
        return # wait between button presses
    
    current_state = button_up
    light_on = (relay_pin.value() == 1)
    time.sleep(0.05)
    button_up = push_button.value()
    log.debug(f'Relay: {relay_pin.value()} LED: {led.value()} Light_on: {light_on}')
    if not button_up and button_up == current_state:
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
        

def set_mode()->bool:
    global light_on
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
        for start,end in data['timers']:
            if start <= the_time and end >= the_time:
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
        
    return new_mode
    
    
async def manage_mode():
    global delay_time, blink_delay, blink_times, relay_pin, light_on
    new_mode = set_mode()
    data = json.loads(get_status_from_file())
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
    global blink_times
    blink_times = 2
    return json.dumps(add_light_state(get_status_from_file()))

def update(data):

##### TODO #####
# This needs to be more robust to validate the data
###############################

    if data:        
        save_status_to_file(data)

#     manage_mode()
    
    content = json.loads(data)
    content = add_light_state(content)
    return json.dumps(content)

def add_light_state(content: str | dict)->dict:
    set_mode()
    if isinstance(content,str):
        content = json.loads(content)
    content.update({"light_on":light_on})
    return content


# Asynchronous functio to handle client's requests
async def handle_client(reader, writer):
    addr, prt = reader.get_extra_info('peername')
    request = ''
    response = ''
    request_data = 'No data here'
    fields = {}

    if addr == '68.66.224.2' or addr.startswith('192'):
        try:
            log.info(f"Client {addr} connected")
            request_line = await reader.readline()
            request = str(request_line, 'utf-8').split()[1]
            method = str(request_line, 'utf-8').split()[0].upper()
            # read the headers
            headers = {}
            while True:
                try:
                    tmp = await reader.readline()
                    if tmp != b"\r\n":
                        h,v = tmp.decode().replace(':','').split()
                        headers[h] = v
                    else:
                        break
                except Exception:
                    pass
                    
#             print(headers)
            if method == 'POST' and 'Content-Length' in headers:
                # get the posted data as a json string
                request_data = await reader.read(int(headers['Content-Length']))
#                 print(request_data)

        except Exception as e:
            log.exception(e,"Handle Client, Bad Request")
            request = "Bad Request"
    else:
        request = f'Rejected client at {addr}'
        log.info(request)
        
    if request == '/lights/status.json':
        response = status()
#         print(f'Status {response=}')

    elif request == '/lights/update':
#         print(f'{request=}')
        response = update(request_data.decode())
#         print(f'Update {response=}')

        
    if response:
        # Send the HTTP response and close the connection
        writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    else:
        writer.write('HTTP/1.0 404 NOT FOUND\r\nContent-type: text/html\r\n\r\n')
        response = 'Page Not Found'
                
    writer.write(response)
    await writer.drain()

    await writer.wait_closed()
    log.info('Client Disconnected')
    

async def main():
    global blink_times
    if not connection.is_connected():
        connection.connect()
    if not rtc.has_time:
        rtc.set_time()
    
    # Start the server and run the event loop
    print('Setting up server')
    print('connected at',connection.wlan.ipconfig('addr4')[0])
    server = asyncio.start_server(handle_client, "0.0.0.0", 80)
    asyncio.create_task(server)
    asyncio.create_task(manage_mode())
    asyncio.create_task(handle_button())
    asyncio.create_task(blink())
    
    blink_times = 2

    while True:
        try:
            # Add other tasks that you might need to do in the loop
            await asyncio.sleep(0.5) # a delay is needed to give server some time to work
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
    log.exception(e,'Error occurred in module')
    soft_reset
except KeyboardInterrupt:
    log.info('Program Interrupted by the user')