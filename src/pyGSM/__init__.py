''' The PyGSM Library '''
import serial_port    ### serial port sniffer with class
import os
import signal
import time
import sys
import fcntl


''' -------------------- The GSM class --------------------------- '''
class gsm(object):
    def __init__(self, port='', log_folder_path='.'):
        ### Create a serial port object to access buffer files
        self.usb = serial_port.port(port, log_folder_path)

        self.call_in_log = log_folder_path + '/' + port + '/call_in_log.txt'

        self.call_wait_log = log_folder_path + '/' + port + '/call_wait_log.txt'

        self.call_out_log = log_folder_path + '/' + port + '/call_out_log.txt'

        ### Initialize state to "Call Disconnect State"
        self.call_state = '6' 

        self.cclk={}

        self.alarm_flag = 0

        self.call_in_ctr = 0
        self.call_wait_ctr = 0
        self.call_out_ctr = 0        

    def __del__(self):
        ### While object being deleted, disconnect call 
        self.disconnect_call()
        del self.usb

    def call_in_list(self):
        f = open (self.call_in_log,'a+')
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(self.call_number+'\n')
        f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)        
        f.close()
        self.call_in_ctr += 1
        
    def call_wait_list(self):
        f = open (self.call_wait_log,'a+')
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(self.call_number+'\n')
        f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)        
        f.close()
        self.call_wait_ctr += 1

    def call_out_list(self):
        f = open (self.call_out_log,'a+')
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(self.call_number+'\n')
        f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)        
        f.close()
        self.call_out_ctr += 1

        
    ''' Read from input buffer and remove newline and carriage returns '''
    def readusb(self):
        return self.usb.readline().replace('\n','').replace('\r','')

    ''' Check for OK/ERROR from GSM modem '''
    def isOK(self):
        while True:
            try:
                line = self.readline()        
                if line:
                    if 'OK' in line: return True
                    elif 'ERROR' in line: return False
            except Exception as error:
                print 'Runtime error is: ', error
                return False

    ''' ATE Set Command Echo Mode '''
    def command_echo(self, state): 
        if state == 'OFF':
            self.usb.write('ATE0\n')
        elif state == 'ON':
            self.usb.write('ATE1\n')
        else: raise ValueError

        if self.isOK(): return True                
        else: return False

    ''' AT&W Store Active Profile '''
    def store_profile(self): 
        self.usb.write('AT&W\n')        
        
        if self.isOK(): return True                
        else: return False

    ''' AT+CFUN Set Phone Functionality '''
    def phone_functionality(self, state):
        if state == 'OFF': self.usb.write('at+cfun=0\n')
        elif state == 'ON': self.usb.write('at+cfun=1\n')
        elif state == 'RESTART': 
            self.usb.write('at+cfun=1,1\n')
            
            ### On restart, wait for call ready
            try:
                while not 'Call Ready' in self.readline(): pass
            except:
                while not 'Call Ready' in self.readline(): pass

            ### Disable command echo
            self.command_echo('OFF')

            return True
        else: raise ValueError

        if self.isOK():    return True
        else: return False
    
    ''' AT+CCALR Call Ready Query '''
    def call_ready(self):
        temp = False
        self.usb.write('at+ccalr?\n')
        line = self.readline()
        while not 'OK' in line:
            if '+CCALR:' in line:
                temp = bool(int(line.split(':')[1].replace(' ','')))
            line = self.readline()
        #print 'Call Ready: ', temp
        return temp
                
    ''' 
        AT+CLCC List Current Calls of GSM modem - Autoreport on change in call
        status 
    '''
    def current_calls_report(self, state):
        if state == 'OFF':
            self.usb.write('AT+CLCC=0\n')
        elif state == 'ON':
            self.usb.write('AT+CLCC=1\n')
        else: raise ValueError

        if self.isOK(): return True                
        else: return False

    ''' AT+CLCC List Current Calls of GSM modem - To check for active calls '''
    def check_current_calls(self):
        temp = False        
        self.usb.write('AT+CLCC\n')
        line = self.readline()
        while not (('OK' in line) or ('ERROR' in line)):
            if '+CLCC:' in line: temp = True
            line = self.readline()
        return temp
        
    ''' 
        Parse the auto report from AT+CLCC when call state changes 
        +CLCC: <id>,<dir>,<stat>,<mode>,<mpty>,"<number>",<type>,"<alphaID>"
        0. <id>            - call ID number
        1. <dir>        - 0 Mobile originated (MO) call
                          1 Mobile terminated (MT) call
        2. <stat>        - State of the call:
                          0 Active
                          1 Held
                          2 Dialing (MO call)
                          3 Alerting (MO call)
                          4 Incoming (MT call)
                          5 Waiting (MT call)
                          6 Disconnect
        3. <mode>        - Bearer/tele service:
                          0 Voice
                          1 Data
                          2 Fax
        4. <mpty>        - 0 Call is not one of multiparty (conference) call
                          1 Call is one of multiparty (conference) call 
        5. "<number>"    - Phone number in string type 
                          (should be included in quotation marks)
        6. <type>        - Type of address
        7. "<alphaID>"    - Name associated to phone number, in the phonebook
    '''
    def parse_current_calls(self, line):
        line = line.split(':')[1]
        line = line.split(',')
        #self.call_id = line[0]
        self.call_direction = line[1]
        self.call_state = line[2]
        self.call_number = line[5].replace('"','')        

    '''
        Send command AT to GSM modem and wait 3s for reply
    '''    
    def modem_connect(self):
        def gsm_connect_wait(signum, frame):
            raise Exception    

        signal.signal(signal.SIGALRM, gsm_connect_wait)

        signal.alarm(3)
        try:
            temp = ''
            self.usb.write('at\n')
            temp = self.readusb()
            while not temp: temp = self.readusb()
        except: 
            print 'Please connect GSM modem'
            return False
        signal.alarm(0)
        return True

    ''' 
        Method to read the input buffer file
        While reading the buffer file it checks for
        01. Any calls and their status
        02. +CPIN: NOT READY - This usually indicates bad network
            Restart phone functionality when encountered. 
        03. +CFUN: 1 - indicates modem  restarted. Disable command echo
        04. Alarms - update the alarm flag with the alarm number
    '''
    def readline(self):
        line = self.readusb()
        if line: 
            if '+CLCC:' in line: 
                self.parse_current_calls(line)
                if self.call_direction == '1':
                    if self.call_state == '5' and self.call_number:
                        self.call_wait_list()
                        print 'Call Waiting from: ', self.call_number
                    elif self.call_state == '4' and self.call_number:
                        self.call_in_list()
                        print 'Incoming Call from: ', self.call_number
                if self.call_direction == '0':
                    if self.call_state == '6': 
                        self.call_out_list()
                        print "Raised Call Termination"
                        raise Exception ("Call Terminated")
            elif '+CPIN: NOT READY' in line: 
                print 'Modem restart: ', self.phone_functionality('RESTART')
                raise Exception("SIM Card Not Inserted Properly")
            elif '+CFUN: 1' in line: 
                self.command_echo('OFF')
                self.local_timestamp('OFF')
                raise Exception("Call Terminated, Modem Restarted")
            elif 'ALARM' in line:
                line = self.readusb()
                while '+CALV' not in line: line = self.readusb()
                self.alarm_flag = int(line.split(':')[1])
            return line    
        return ''

    '''
        ATD Mobile Originated Call to Dial A Number
        Also monitor status of the dialed call
    '''
    def dial_number(self,number):
        ring = 0
        if self.check_current_calls():  return 'Busy'
        else:
            self.usb.write('ATD'+number+';\n')
            if self.isOK():
                try: 
                    time.sleep(3)
                    line = self.readline()
                    while not (self.call_direction == '0' and self.call_state == '0'): 
                        line = self.readline()
                        if self.call_state == '3': ring = 1
                    return 'Call Established'
                except Exception as error: 
                    print 'Alert: ', error
                    if ring: return 'Call Not Answered'
                    return 'Call Connection Failed'
            return 'Dialing Failed'

    ''' 
        AT+DDET DTMF Detection Control 
        with default 1000ms interval for two same keypress 
    '''
    def dtmf_detection(self, state, interval = '1000'):
        if state == 'OFF':
            self.usb.write('AT+DDET=0\n')
        elif state == 'ON':
            self.usb.write('AT+DDET=1,'+interval+'\n')
        else: raise ValueError

        if self.isOK(): return True                
        else: return False

    ''' AT+CLIP Calling Line Identification Presentation '''
    def clip(self, state):
        if state == 'OFF':
            self.usb.write('AT+CLIP=0\n')
        elif state == 'ON':
            self.usb.write('AT+CLIP=1\n')
        else: raise ValueError

        if self.isOK(): return True                
        else: return False

    ''' 
        AT+CCWA Call Waiting Control
        <n>        - 0 Disable alert on incoming call wait
                  1 Enable alert on incoming call wait
        <mode>     - 0 Disable
                - 1 Enable
    '''
    def call_wait_control(self, state, report='0'):
        if state == 'OFF':
            self.usb.write('AT+CCWA='+report+',0\n')
        elif state == 'ON':
            self.usb.write('AT+CCWA='+report+',1\n')
        else: raise ValueError

        if self.isOK(): return True                
        else: return False
    
    ''' ATH Disconnect Existing Connection '''
    def disconnect_call(self):
        self.usb.write('ATH\n')
        if self.isOK(): return True                
        else: return False

    ''' AT+CLTS Get Local Timestamp from the network '''
    def local_timestamp(self, state):
        if state == 'OFF':
            self.usb.write('AT+CLTS=0\n')
        elif state == 'ON':
            self.usb.write('AT+CLTS=1\n')
        else: raise ValueError

        if self.isOK(): return True                
        else: return False

        
    ''' AT+MORING Show State of Mobile Originated Call '''
    def outgoing_call_status(self, state):
        if state == 'OFF':
            self.usb.write('AT+MORING=0\n')
        elif state == 'ON':
            self.usb.write('AT+MORING=1\n')
        else: raise ValueError

        if self.isOK(): return True                
        else: return False

    ''' To clear stray DTMF presses '''
    def clear_dtmf(self):
        i = 0
        while i<5:
            x=self.readline()
            #print 'Things to Clear', x
            if not x: i += 1
            else: i = 0

    ''' Parse response from modem and obtain the DTMF value '''
    def read_dtmf(self):
        line = self.readline()
        if '+DTMF:' in line:
            self.clear_dtmf()        #to ignore multiple key press
            return line.split(':')[1].replace(' ','')
        return ''

    ''' Get Time '''
    def get_clock(self):
        self.usb.write('AT+CCLK?\n')
        
        line = self.readline()
        while not line: line = self.readline()
        if '+CCLK:' in line:
            temp = line.split('"')[1]
            temp_date = temp.split(',')[0].split('/')
            temp_time = temp.split(',')[1].split(':')
            self.cclk['year'] = 2000 + int(temp_date[0])
            self.cclk['month'] = int(temp_date[1])
            self.cclk['day'] = int(temp_date[2])
            self.cclk['hour'] = int(temp_time[0])
            self.cclk['min'] = int(temp_time[1])
            self.cclk['sec'] = int(temp_time[2].split('+')[0])
            self.cclk['timezone'] = int(temp_time[2].split('+')[1])
            if self.isOK(): return self.cclk
        return {}

    def set_alarm(self, time, id_no, *repeat):
        self.del_alarm(id_no)

        alarm_string = list(repeat)
        alarm_string.insert(0, time)
        alarm_string.insert(1, id_no)
        alarm_string = [str(i) for i in alarm_string]
        alarm_string[0] = '"' + alarm_string[0] + '"'
        alarm_string = ','.join(alarm_string)
        
        self.usb.write('AT+CALA='+alarm_string+'\n')

        if self.isOK(): return True                
        else: return False

    def check_alarm(self, id_no):
        flag = False        
        self.usb.write('AT+CALA?\n')
        
        line = self.readline()
        while 'OK' not in line: 
            if '+CALA' in line:
                #print 'Line :', line
                #raw_input()
                parsing = line.split(',')[1]
                if id_no == int(parsing):
                    flag = True                
            line = self.readline()        
        return flag
        
    def del_alarm(self, id_no):
        if self.check_alarm(id_no):
            self.usb.write('AT+CALD='+str(id_no)+'\n')

            if self.isOK(): return True                
        return False
        
        
    #''' Set Time '''
    #def set_clock(self):
        
    

if __name__ == '__main__':

    try:
        mygsm = gsm(sys.argv[1],'/../../data/log/')
    except:
        print 'Serial Port ID needs to be passed!!!'
        exit()
    '''while not mygsm.modem_connect(): time.sleep(3)
    #if not mygsm.call_ready(): mygsm.phone_functionality('RESTART')
    print 'Echo OFF: ', mygsm.command_echo('OFF')
    #print 'Phone ON: ', mygsm.phone_functionality('ON')

    print 'Alert on change in call status: ', mygsm.current_calls_report('ON')
    raw_input()'''

    while not mygsm.modem_connect(): time.sleep(3)
    print 'Echo OFF: ', mygsm.command_echo('OFF')
    print 'Get SIM Time: ', mygsm.local_timestamp('ON')
    print 'Save Profile: ', mygsm.store_profile()
    mygsm.phone_functionality('RESTART')
    time.sleep(3)
    chk = mygsm.call_ready()
    print 'Call Ready: ', chk
    if not chk: 
        mygsm.phone_functionality('RESTART')
    print 'Alert on change in call status: ', mygsm.current_calls_report('ON')
    print 'Caller ID disabled during incoming call: ', mygsm.clip('OFF')
    print 'Call Waiting enabled: ', mygsm.call_wait_control('ON')
    print 'Outgoing call status indication: ', mygsm.outgoing_call_status('OFF')
    print 'Get SIM Time: ', mygsm.local_timestamp('OFF')

    clck = mygsm.get_clock()
    print 'Clock says: ', clck
    print 'hour is :', clck['hour']

    print 'Alarm x exists and deleted: ', mygsm.set_alarm("17:00:00",2,5,6,7)

    while True:
        mygsm.readline()
    
