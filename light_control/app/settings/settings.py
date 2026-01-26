# System setting

from machine import Pin, SPI, SoftSPI
from logging import logging as log
from wifi_connect import connection
if connection.wifi_available:
    import urequests
    
import json
import os
import time

class Settings:
    
    def __init__(self,debug=False):
        self.debug = debug
        self.UTC_offset = -8
        self.host = 'http://williesworkshop.net'
        
    @property    
    def ota_source_url(self):
        dest = '/api/check_file_version'
        return f'{self.host}{dest}'
    


settings = Settings()
