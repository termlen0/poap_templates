#!/bin/env python
#md5sum="a6d7571af80c076e4587268c1ac0b15e"
"""
If any changes are made to this script, please run the below command
in bash shell to update the above md5sum. This is used for integrity check.
f=poap_nexus_script.py ; cat $f | sed '/^#md5sum/d' > $f.md5 ; sed -i \
"s/^#md5sum=.*/#md5sum=\"$(md5sum $f.md5 | sed 's/ .*//')\"/" $f
"""

import urllib2
import json
import syslog
import sys
import signal
from time import gmtime, strftime
import re
import glob
# Libraries to allow cli commands from python
try:
    from cisco import cli
    from cisco import transfer
    legacy = True
except ImportError:
    from cli import *
    legacy = False

#End user is expected to modify the options dict
options = {
    "remote_server": "2.1.1.1",
    "protocol": "tftp", # Current support only for HTTP/TFTP
    "port": "69",
    "identifier": "080027F494FB", # MAC or S.No of device
    "disable_md5": True,
}


""" 
If HTTP is being used, ensure that the desired config is returned by accessing the URI as follows:
URL : http://ntc.api:3000/080027F494FB

Response:
[
  {
    "config": "vdc switch id 1\n  limit-resource vlan minimum 16 maximum 4094\n  limit-resource vrf minimum 2 maximum 4096\n  limit-resource port-channel minimum 0 maximum 511\n  limit-resource u4route-mem minimum 248 maximum 248\n  limit-resource u6route-mem minimum 96 maximum 96\n  limit-resource m4route-mem minimum 58 maximum 58\n  limit-resource m6route-mem minimum 8 maximum 8\nfeature bash-shell\nfeature ssh\n\nhostname nxosv\n\nno password strength-check\nusername admin password 5 $5$bFlOCeX2$Bgnf4kzZPWPkekMalE84W1uKRlG705WCn141FZLOCWC  role network-admin\nusername vagrant password vagrant role network-admin\nusername vagrant shell bash\nip domain-lookup\nsnmp-server user admin network-admin auth md5 0xbb785c32a1b11f4d7f4c406ce877163a priv 0xbb785c32a1b11f4d7f4c406ce877163a localizedkey\nrmon event 1 log trap public description FATAL(1) owner PMON@FATAL\nrmon event 2 log trap public description CRITICAL(2) owner PMON@CRITICAL\nrmon event 3 log trap public description ERROR(3) owner PMON@ERROR\nrmon event 4 log trap public description WARNING(4) owner PMON@WARNING\nrmon event 5 log trap public description INFORMATION(5) owner PMON@INFO\n\nusername vagrant sshkey ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEA6NF8iallvQVp22WDkTkyrtvp9eWW6A8YVr+kz4TjGYe7gHzIw+niNltGEFHzD8+v1I2YJ6oXevct1YeS0o9HZyN1Q9qgCgzUFtdOKLv6IedplqoPkcmF0aYet2PkEDo3MlTBckFXPITAMzF8dJSIFo9D8HfdOV0IAdx4O7PtixWKn5y2hMNG0zQPyUecp4pzC6kivAIhyfHilFR61RGL+GPXQ2MWZWFYbAGjyiYJnAmCP3NOTd0jMZEnDkbUvxhMmBYSdETk1rRgm+R4LOzFUGaHqHDLKLX+FIPKcF96hrucXzcWyLbIbEgE98OHlnVYCzRdK8jlqm8tehUc9c9WhQ== vagrant insecure public key\n\nvlan 1\n\nvrf context management\n\ninterface Ethernet1/1\n  no switchport\n  ip address 20.1.1.1/24\n  no shutdown\n\ninterface Ethernet1/2\n  no switchport\n  ip address 100.1.1.1/24\n  no shutdown\n\ninterface mgmt0\n  vrf member management\n  ip address dhcp\nline console\nline vty\n",
    "md5sum": "somedata"
  }
]

"""



def tftp_copy():
    """ Copies the config file over TFTP"""
    file_name = "conf_{0}.cfg".format(options['identifier'])
    vrf = "Management"
    host = options['remote_server']
    poap_log("Transfering config file {} over TFTP".format(file_name))
    copy_cmd = "terminal dont-ask ; "
    copy_cmd += "copy tftp://%s/%s bootflash:/%s vrf %s" % (host, file_name, file_name , vrf)
    poap_log("Command is : %s" % copy_cmd)
    try:
        cli(copy_cmd)
    except Exception as e:
        # Remove extra junk in the message
        if "no such file" in str(e):
            abort("Copy of %s failed: no such file" % source)
        elif "Permission denied" in str(e):
            abort("Copy of %s failed: permission denied" % source)
        elif "No space left on device" in str(e):
            abort("No space left on device")
        else:
            raise
    # TODO: MD5 sum validation 
    poap_log("Copy over TFTP, complete")


def http_copy():
    """ Copies the config file over HTTP"""
    file_name = "conf_{0}.cfg".format(options['identifier'])
    port = options['port']
    host = options['remote_server']
    id = options['identifier']
    poap_log("Transfering config file {} over HTTP".format(file_name))
    try: 
        response = urllib2.urlopen('http://{}:{}/{}'.format(host, port, id)).read()
    except Exception:
        e_type, e_val, e_trace = sys.exc_info()
        poap_log("Exception: {0} {1}".format(e_type, e_val))
        while e_trace is not None:
            fname = os.path.split(e_trace.tb_frame.f_code.co_filename)[1]
            poap_log("Stack - File: {0} Line: {1}"
                     .format(fname, e_trace.tb_lineno))
            e_trace = e_trace.tb_next
            abort()
    # Convert the data into a dict
    data = json.loads(response)
    poap_log("Data collected from HTTP request")
    # Write the config locally to a file
    dest = '/bootflash/{}'.format(file_name)
    try: 
        with open(dest, 'w') as fh:
            fh.write(data[0]['config'])
    except Exception:
        e_type, e_val, e_trace = sys.exc_info()
        poap_log("Exception: {0} {1}".format(e_type, e_val))
        while e_trace is not None:
            fname = os.path.split(e_trace.tb_frame.f_code.co_filename)[1]
            poap_log("Stack - File: {0} Line: {1}"
                     .format(fname, e_trace.tb_lineno))
            e_trace = e_trace.tb_next
            abort()
    # TODO: MD5 sum validation 
    poap_log("Config data copied successfully to bootflash")


def setup_logging():
    """
    Configures the log file this script uses
    """
    global log_hdl, syslog_prefix
    syslog_prefix = options['identifier']
    poap_script_log = "/bootflash/%s_poap.log" % (strftime("%Y%m%d%H%M%S", gmtime()))
    log_hdl = open(poap_script_log, "w+")
    poap_log("Logfile name: %s" % poap_script_log)
    poap_cleanup_script_logs()

    
def poap_log(info):
    """
    Log the trace into console and poap_script log file in bootflash
    Args:
        file_hdl: poap_script log bootflash file handle
        info: The information that needs to be logged.
    """
    global log_hdl, syslog_prefix
    # Don't syslog passwords
    parts = re.split("\s+", info.strip())
    for (index, part) in enumerate(parts):
        # blank out the password after the password keyword (terminal password *****, etc.)
        if part == "password" and len(parts) >= index+2:
            parts[index+1] = "<removed>"
    # Recombine for syslogging
    info = " ".join(parts)
    # We could potentially get a traceback (and trigger this) before
    # we have called init_globals. Make sure we can still log successfully
    try:
        info = "%s - %s" % (syslog_prefix, info)
    except NameError:
        info = " - %s" % info
    syslog.syslog(9, info)
    if "log_hdl" in globals() and log_hdl is not None:
        log_hdl.write("\n")
        log_hdl.write(info)
        log_hdl.flush()

        
def poap_cleanup_script_logs():
    """
    Deletes all the POAP log files in bootflash leaving
    recent 4 files.
    """
    file_list = sorted(glob.glob(os.path.join("/bootflash", '*poap.log')), reverse=True)
    poap_log("Found %d POAP script logs" % len(file_list))
    logs_for_removal = file_list[4:]
    for old_log in logs_for_removal:
        remove_file(old_log)

        
def remove_file(filename):
    """
    Removes a file if it exists and it's not a directory.
    """
    if os.path.isfile(filename):
        try:
            os.remove(filename)
        except (IOError, OSError) as e:
            poap_log("Failed to remove %s: %s" % (filename, str(e)))

def abort(msg=None):
    """
    Aborts the POAP script execution with an optional message.
    """
    global log_hdl

    if msg is not None:
        poap_log(msg)

    # Remove config _file(<path to config file>)
    remove_file(os.path.join("/bootflash", "conf_{0}.cfg".format(options['identifier'])))
    # Close the log file
    if log_hdl is not None: 
        log_hdl.close()
    exit(1)            

def sigterm_handler(signum, stack):
    """
    A signal handler for the SIGTERM signal. Cleans up and exits
    """
    abort("INFO: SIGTERM Handler")
    
def copy_config(protocol):
    # Register the SIG TERM handler
    signal.signal(signal.SIGTERM, sigterm_handler)
    if protocol == "tftp":
        tftp_copy()
    elif protocol == "http":
        http_copy()
    cmd = "terminal dont-ask ;"
    cmd += "copy bootflash:/conf_{}.cfg scheduled-config".format(options['identifier'])
    poap_log("INFO: Ready to execute {}".format(cmd))
    try:
        cli(cmd)
    except Exception:
        e_type, e_val, e_trace = sys.exc_info()
        poap_log("Exception: {0} {1}".format(e_type, e_val))
        while e_trace is not None:
            fname = os.path.split(e_trace.tb_frame.f_code.co_filename)[1]
            poap_log("Stack - File: {0} Line: {1}"
                     .format(fname, e_trace.tb_lineno))
            e_trace = e_trace.tb_next
            abort()

def image_install():
    pass

def main():
    # Download and Install the user requested image
    image_install()
    copy_config(options['protocol'])
    
    

            
            
    

        
if __name__ == "__main__":
    #Start logging 
    setup_logging()
    try:
        main()
    except Exception:
        e_type, e_val, e_trace = sys.exc_info()
        poap_log("Exception: {0} {1}".format(e_type, e_val))
        while e_trace is not None:
            fname = os.path.split(e_trace.tb_frame.f_code.co_filename)[1]
            poap_log("Stack - File: {0} Line: {1}"
                     .format(fname, e_trace.tb_lineno))
            e_trace = e_trace.tb_next
            abort()



        
            
