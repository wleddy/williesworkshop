"""Keep a list of the files that need to be checked
for OTA updates here."""

def get_ota_file_list():
    return [ 
        'main.py',
        'settings/time_functions.py',
        'settings/credentials.conf',
        'settings/settings.py',
        'settings/tickle.txt',
        'lib/ota_update/ota_update.py',
        'lib/ota_update/check_for_updates.py',
        'lib/ntp_clock.py',
        'lib/wifi_connect.py',
        'lib/os_path.py',
        'lib/logging/logging.py',
        ]
