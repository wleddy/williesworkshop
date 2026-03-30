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

class LightControl:
    
    DATA_FILE = "instance/lights.json"
    CLOCK_RESET_INTERVAL = 3600 #set the clock at lease this many seconds
    
    def __init__(self):
        self.led = Pin(26, Pin.OUT)
        self.led.off()
        self.on_board_led = Pin('LED',Pin.OUT)
            
        self.relay_pin = Pin(10, Pin.OUT) # was 15 ... 15 may be toasted?
        self.relay_pin.off()
        self.push_button = Pin(14,Pin.IN,Pin.PULL_UP)
        self.push_button_led = PWM(12, freq=300, duty_u16=65536//4) # reduce the brightness of the button self.led
        
        connection.connect()

        self.rtc = Clock()
        self.rtc_last_set = 0 #force reset
        self.set_clock()

        self.delay_time = -1
        self.blink_delay = 0.5
        self.blink_times = 0
        self.button_buffer_ticks = time.ticks_ms()
        self.light_on = False

    def set_led(self,val):
        # keep the onboard and external self.leds in syinc
        self.led.value(val)
        self.on_board_led.value(val)


    async def blink(self):
        val = self.led.value()
        self.blink_times = int(self.blink_times)
        while self.blink_times > 0:
            for z in range(2):
                val = 1 if val == 0 else 0
                self.set_led(val)
                log.debug(f'Blink = Relay: {self.relay_pin.value()} self.led: {self.led.value()}')
                await asyncio.sleep(self.blink_delay)
            self.blink_times -= 1
        self.set_led(self.relay_pin.value())
        # reset to defaults
        self.blink_delay = 0.5
        self.blink_times = 0


    async def handle_button(self):
        button_up = self.push_button.value()
        if button_up or self.button_buffer_ticks > time.ticks_ms():
            return # wait between button presses
        
        current_state = button_up
        self.light_on = (self.relay_pin.value() == 1)
        time.sleep(0.05)
        button_up = self.push_button.value()
        log.debug(f'Relay: {self.relay_pin.value()} self.led: {self.led.value()} self.light_on: {self.light_on}')
        if not button_up and button_up == current_state:
            data = json.loads(self.get_status_from_file())
            val = 0 if self.led.value() == 1 else 1
            self.set_led(val)

            if self.light_on:
                data['mode'] = 3 # off till next
            else:
                data['mode'] = 2 # on till next
             
            # used to delay a bit before processing another press
            self.button_buffer_ticks = time.ticks_ms() + 2000

            # save the new status
            log.info(f'Button pressed, Mode: {data["mode"]}')
            self.save_status_to_file(json.dumps(data))
            

    def set_mode(self)->bool:
        try:
            if not connection.is_connected():
                connection.connect()
            if not self.rtc.has_time:
                self.rtc.set_time()
            the_time = self.rtc.time_string(format=24)
            if the_time == '--:--':
                the_time = None
        except:
            the_time = None
            
        data = json.loads(self.get_status_from_file())
        timer_on = False
        self.light_on = False
        new_mode = data.get('mode',-1)

        if 'timers' in data and the_time:
            for start,end in data['timers']:
                if start <= the_time and end >= the_time:
                    timer_on = True
                    break

        state = data.get('mode',0) # turn off by default for safety
        if state == -1 and timer_on: #auto
            self.light_on = True
        elif state == 0: #Always off
            self.light_on = False
        elif state == 1: #Always On
            self.light_on = True
        elif state == 2 and timer_on: #on till next
            self.light_on = True
            new_mode = -1 # set back to auto
        elif state == 2 and not timer_on: #on till next
            self.light_on = True
        elif state == 3 and timer_on: #Off till next
            self.light_on = False
        elif state == 3 and not timer_on:
            self.light_on = False
            new_mode = -1 #set back to auto
            
        return new_mode
        
        
    async def manage_mode(self):
        new_mode = self.set_mode()
        data = json.loads(self.get_status_from_file())
        if self.light_on:
            self.delay_time = 0
            self.relay_pin.value(1)
            log.debug(f'manage_mode = (Turn on light) Relay: {self.relay_pin.value()}, self.light_on: {self.light_on}')
        else:
    #         print('self.delay_time:',self.delay_time,'Time:',time.time())
            if self.delay_time == 0:
                self.delay_time = time.time() + data.get('delay_seconds',0)
        #       print('self.delay_time set to:',self.delay_time,'Time:',time.time())
                self.blink_delay = 1
                self.blink_times = data.get('delay_seconds',0)

            elif time.time() >= self.delay_time:
                self.relay_pin.off()
                
        # save the data?
        if new_mode != data.get('mode'):
            data['mode'] = new_mode
            log.info(f'saving: {data}')
            self.save_status_to_file(json.dumps(data))
            
        log.debug(f'manage_mode = Relay: {self.relay_pin.value()} self.led: {self.led.value()} self.light_on: {self.light_on}')

    def save_status_to_file(self,data):
        make_path('/',self.DATA_FILE)
        with open(self.DATA_FILE,'w') as f:
                f.write(data)

    def get_status_from_file(self)->str:
        default_content = '{"mode":-1,delay_seconds":10, "timers":[["17:00","22:00"]]}' # default value
        content = ''
        try:
            with open(self.DATA_FILE,"r") as f:
                content = f.read()
        except:
            pass
        
        if not content:
            content = default_content
            log.info("using default data")

        return content

#     def decode(self,data:str)->str:
#         # decode json text 
#         data = data.replace('%7B','{')
#         data = data.replace('%7D','}')
#         data = data.replace('%22','"')
#         data = data.replace('%3A',':')
#         data = data.replace('+',' ')
#         data = data.replace('%2C',',')
#         data = data.replace('%5B','[')
#         data = data.replace('%5D',']')
#         data = data.replace('%20',' ')
#         return data

    def status(self)->str:
        self.blink_times = 2
        return json.dumps(self.add_light_state(self.get_status_from_file()))

    def update(self,data:str)->str:

    ##### TODO #####
    # This needs to be more robust to validate the data
    ###############################

        if data:        
            self.save_status_to_file(data)
        
        content = json.loads(data)
        content = self.add_light_state(content)
        return json.dumps(content)

    def add_light_state(self,content: str | dict)->dict:
        self.set_mode()
        if isinstance(content,str):
            content = json.loads(content)
        content.update({"light_on":self.light_on})

        return content


    # Asynchronous functio to handle client's requests
    async def handle_client(self,reader, writer)->None:
        addr, prt = reader.get_extra_info('peername')
        request = ''
        response = ''
        request_data = 'No data here'

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
            response = self.status()
    #         print(f'Status {response=}')

        elif request == '/lights/update':
            response = self.update(request_data.decode())
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
        
    async def set_clock(self)->None:
        if not self.rtc.has_time \
           or time.time() > self.rtc_last_set + self.CLOCK_RESET_INTERVAL:
            try:
                self.rtc.set_time()
                self.rtc_last_set = time.time()
            except:
                # usually a communication error
                pass
            
    async def main(self):
        await self.set_clock()
        
        # Start the server and run the event loop
        print('Setting up server')
        print('connected at',connection.wlan.ipconfig('addr4')[0])
        server = asyncio.start_server(self.handle_client, "0.0.0.0", 80)
        asyncio.create_task(server)
        asyncio.create_task(self.manage_mode())
        asyncio.create_task(self.handle_button())
        asyncio.create_task(self.blink())
        asyncio.create_task(self.set_clock())
        
        self.blink_times = 2

        while True:
            try:
                # Add other tasks that you might need to do in the loop
                await asyncio.sleep(0.5) # a delay is needed to give server some time to work
                await self.manage_mode()
                await self.blink()
                await self.handle_button()
                await self.set_clock()
            except Exception as e:
                log.error(f'Main loop error: {str(e)}')

# Create an Event Loop
loop = asyncio.get_event_loop()
# Create a task to run the main function
light = LightControl()
loop.create_task(light.main())

try:
    # Run the event loop indefinitely
    loop.run_forever()
except Exception as e:
    log.exception(e,'Error occurred in module')
    soft_reset
except KeyboardInterrupt:
    log.info('Program Interrupted by the user')