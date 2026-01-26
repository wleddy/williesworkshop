from logging import logging as log

try:
    import network
except ImportError:
    pass

import time
import json
import sys

class Wifi_Connect:
    
    def __init__(self,credentials="settings/credentials.conf"):
        self.credentials = credentials
        self.access_point = ""
        _machine = sys.implementation._machine
        self.wifi_available = True
        if not 'Pico W' in _machine:
            log.info(f'No WiFi available on {_machine}')
            self.wifi_available = False
            return

        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(False)
        self.wlan.disconnect() # may not be needed
        
    def connect(self):
        if not self.wifi_available:
            return
        
        if self.isconnected():
            return
        log.info('connecting...')
        self.wlan.active(True)
        # try to use last connection
        last_dict = self._last_ssid()
        if last_dict:
            # get the first and only key
            for name in last_dict:
                break # first value is loaded in  name
            
            self._connect_from_list([name],last_dict)

        if not self.access_point:
            log.info('scan for available access points')
            scan = self._scan()

            # open the credentials file
            # each line contains <ssid,password>
            c = []
            try:
                with open(self.credentials) as f:
                    c = f.readlines()
                log.debug("ssid_credentials: {str(c)}")
            except Exception as e:
                log.exception(e,str(e))
            
            ssid_credentials = {}
            for x in c:
                l = x.split(",")
                ssid_credentials[l[0].strip()] = None #ssid name without password
                if len(l) == 2:
                    # Has password... update value
                    ssid_credentials[l[0].strip()] = l[1].strip()
                
            # if known_ssids, continue
            if len(ssid_credentials) > 0:
                self._connect_from_list(scan,ssid_credentials)

        if not self.access_point:
            log.info("Unable to connect")
            self.wlan.active(False)
          
    def _last_ssid(self,ssid=None,pw=None):
        """Get or set the last ssid succesfully accessed
        
        always returns a dict
        
        """
        
        if ssid:
            mode = "w"
        else:
            mode = 'r'
 
        out = {}
        
        try:
            with open('/settings/last_ssid.txt',mode) as f:
                if ssid:
                    out = {ssid:pw}
                    f.write(json.dumps(out))
                else:
                    out = json.loads(f.readline())
        except Exception as e:
            log.info("Unable to access last_ssid: {}".format(str(e)))
            
        return out
    
    
    def _connect_from_list(self,ap_list,ap_credentials):
        """ap_list is a list of ap_names in the order to be tried.
        ap_credentials is a dict as:
        {'ap_name':'ap_password',...}
        """

        # try to find one of our credentals to match
        for ap in ap_list:
            log.debug(f"Trying: {ap}")
            if ap in ap_credentials:
                # try to connect to this ap
                log.debug("Connect to {} with key {}".format(ap,ap_credentials[ap]))
                self.wlan.connect(ssid=ap,key=ap_credentials[ap])
                trys = 20
                while trys > 0 and not self.wlan.isconnected():
                    log.debug(f'{trys}: {self.wlan.status()}')
                    time.sleep(.5)
                    trys -= 1
                if self.wlan.isconnected() and self.wlan.status() == network.STAT_GOT_IP:
                    log.info(f"Connected to {ap}")
                    self.access_point = ap
                    #Save credentials for last connection
                    self._last_ssid(ap,ap_credentials[ap])
                    break
                # SSID not connected
                else:
                    if self.wlan.status() == network.STAT_NO_AP_FOUND:
                        reason = "Access Point not found"
                    elif self.wlan.status() == network.STAT_WRONG_PASSWORD:
                        reason = "Wrong Password"
                    else:
                        reason = "Unknown Connection Status ({})".format(self.wlan.status())
                        
                    log.info(f"Connection Failed: {reason}")
                    self.wlan.disconnect()

                        
    def isconnected(self):
        if not self.wifi_available or not self.wlan:
            return False
        return self.wlan.isconnected()

    def is_connected(self):
        # should have had this name all along...
        return self.isconnected()

    def disconnect(self):
        if self.wifi_available and self.wlan:
            self.wlan.disconnect()

    def active(self,state=None):
        if not self.wifi_available or not self.wlan:
            return False
        if state and isinstance(state,bool):
            self.wlan.active(state)
            
        return self.wlan.active()
    
    def status(self):
        if not self.wifi_available:
            return -1 # same as network.STAT_CONNECT_FAIL
        if not self.wlan:
            return network.STAT_IDLE
        else:
            return self.wlan.status()

    def _scan(self):
        if not self.wifi_available:
            return []
        else:
            scan = self.wlan.scan()
            aps_db = []
            aps_names = []
            result = "Scan found: "
            for x in range(4):
                scan = self.wlan.scan()
                for s in scan:
                    name = s[0].decode()
                    if name not in aps_names and name != '':
                        aps_names.append(name)
                        x = "000"+str(abs(s[3]))
                        aps_db.append(x[-3:len(x)]+"/"+name) # we want to sort by db
                result += f", {str(len(aps_db))}"
                time.sleep(1)
                
            log.debug(result)
            
            # sort by best signal strength, lowest first
            aps_db.sort()
            log.debug(f"Scaned: {str(aps_db)}")
            scan=[]
            for l in aps_db:
                scan.append(l.split('/')[1])
                
            return scan

connection = Wifi_Connect() # the connection is not active at this point
