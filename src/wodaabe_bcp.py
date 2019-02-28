import pyGSM        ### for interfacing with GSM modem
import pyIVR
import call_queues
import os            ### for playing the wav files
import sys
import time            ### for delay


''' Getting the path for audio files mainly '''
projectpath =  os.path.split(os.path.realpath(__file__))[0]
audiopath = projectpath + "/../audios"
datapath = projectpath + '/../data'

''' Files used '''
ivr_flow_file = projectpath + '/../docs' + '/wodaabe_bcp_flow.csv'
calls_progress_record = 'call_log.txt'
no_clan_list = datapath + '/clan_not_listed.txt'
log_folder = datapath + '/log'

global mygsm

def ivr_input(is_input):

    dtmf = ''
    try: 
        while mygsm.readline(): pass #clear buffer but scan for call_drop
        
        if is_input == ['']: dtmf = '-'
        
        while not dtmf: dtmf = mygsm.read_dtmf()
        
    except Exception as error:
            print "Error from ivr_input: ", error
            if "Timeout" in error:    dtmf = "noinput" 
            else: dtmf = "exit"

    '''
    if is_input == ['']: 
        dtmf = '-'
        try:
            mygsm.readline()
        except:
            dtmf = "exit"
    
    else:
        mygsm.dtmf_detection("ON")
    
        try:
            dtmf = ''
            
     
        except Exception as error:
            print "Error from ivr_input: ", error
            if "Timeout" in error:    dtmf = "noinput" 
            else: dtmf = "exit"
        
    
        mygsm.dtmf_detection("OFF")
    '''
    
    #print "Call State - ", mygsm.call_state
    #if mygsm.call_state == '6': dtmf = "exit"
    
    print "DTMF = ", dtmf
    return dtmf

if __name__ == "__main__":

    #try:
    mygsm = pyGSM.gsm(sys.argv[1],'/..'+log_folder)
    #except:
    #    print 'Serial Port ID needs to be passed!!!'
    #    exit()
    
    
    

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
    print 'Clock status: ', clck

    print 'Set Alarm at 08:00', mygsm.set_alarm("08:00:00",1,0)
    print 'Set Alarm at 20:00', mygsm.set_alarm("20:00:00",2,0)

    print 'DTMF Detection: ',mygsm.dtmf_detection("ON")
    
    if clck['hour'] > 7 and clck['hour'] < 20:  
        mygsm.alarm_flag = 1
        wakeup_flag = 1
    else: 
        mygsm.alarm_flag = 2
        wakeup_flag = 0


    mygsm.alarm_flag = 1
    wakeup_flag = 1
    #if mygsm.alarm_flag == 1:
    #    print 'Lets do it'
    #else: print 'Wait a minute or rather wait till 08:00'
    
    ### Get the flow sequence of the ivr
    ivr = pyIVR.IvrDialog(csv_file = ivr_flow_file,
                 audiopath = audiopath,
                 datapath = datapath,
                 call_flow_record = calls_progress_record,
                 input_handler = ivr_input,
                 speaker = sys.argv[2],
                 volume = '100'
                 )

    obj = call_queues.monitor_call_logs(log_folder+'/'+sys.argv[1])

    while True:
        
        ### Keep reading the serial port to check for incoming call
        try:
            mygsm.readline()
        except Exception as error: 
            print error 
            pass

        time.sleep(1)
        
        if wakeup_flag and mygsm.alarm_flag == 1:
            obj.wait_to_in()
            wakeup_flag = 0


        if obj.call_to_service and mygsm.call_state == '6' and mygsm.alarm_flag == 2:
            obj.push_wait_queue(obj.call_to_service)
            time.sleep(1)
            print 'Phone number ', obj.call_to_service, ' added to wait list'
            wakeup_flag = 1
            obj.call_to_service = ''
            
        
        elif obj.call_to_service and mygsm.call_state == '6' and mygsm.alarm_flag == 1:
            print('Time to do something')
            print('Calling... '+obj.call_to_service)        
          
       
            phone_number = obj.call_to_service    
            if not phone_number: continue
            print 'Going to call: ', phone_number
            record = ivr.fetch_record(phone_number)
            key = (record[1] if record[1] else '0')
            
            ### if a record for the phone number already exists
            if not key == '0':
                print 'User record exists for ', phone_number

                ### if the record has completed all levels then don't call back
                if key == '113': 
                    print phone_number, ' has already completed the survey'                    
                    #call_queues.wait_to_in()
                    obj.call_to_service = ''
                    continue

            ### call the number
            status = mygsm.dial_number(phone_number)
            print 'Call dial status... ', status
            
            ### if call gets picked up, execute ivr and remove number from list
            if 'Busy' in status: continue
            elif 'Established' in status:
                    ivr.start(phone_number)
                    mygsm.disconnect_call()
                    obj.call_to_service = ''
                    
            elif 'Not Answered' in status: pass
            else: print 'Hanging Up: ', mygsm.disconnect_call()

        
#def zero_back(zero_count):
#    pid = commands.getoutput('ps -a | grep aplay')
#    while pid:
#        if zero_count < 1:
#            dtmf = raw_input()
#            if dtmf == '0':
#                os.system("killall aplay")                    
#                return True            
#        pid = commands.getoutput('ps -a | grep aplay')    
#    return False
    
