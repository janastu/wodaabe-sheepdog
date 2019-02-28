import os
import time
import commands
import subprocess


audio_sinks = ['0000:00:1b.0/sound/card0', 'usb2/2-1/2-1.5/2-1.5:1.0']
pi_audio = ['soc:audio/bcm2835_alsa','usb1/1-1/1-1.4/1-1.4:1.0']

ttyUSB = ['usb 2-1.1', 'usb 2-1.2']
pi_ttyUSB = ['usb 1-1.2','usb 1-1.5']


bcp_path = os.path.split(os.path.realpath(__file__))[0] + '/src' + '/wodaabe_bcp.py'   
bcp = {}
timeout = 3

def get_terminal():
    return commands.getoutput('echo $TERM')

def get_ports():
    ''' Get list of USB Serial Ports connected to the preconfigured USB slots
    '''
    livep = ['']*len(ttyUSB)
    
    ports = commands.getoutput('ls /dev/ | grep ttyUSB')
    if not ports: return livep
    ports = ports.split('\n')

    
    for port in ports:
        x = commands.getoutput("dmesg | grep " + port + " | tail -1")
        for slot in ttyUSB:
            if slot in x: livep[ttyUSB.index(slot)] = port
    return livep


def process_tree(pid):
    ''' Get all the nested child processes' id 
    '''
    tree = []
    while pid:
        tree.append(pid)
        pid = commands.getoutput('ps -o pid= --ppid '+pid)
    return ' '.join(tree)

        
def action_on_ports(old, new):
    ''' When new port (black sheep box) is connected to the right USB slot - 
            start the code if relavant audio card is there
        On disconnect - kill all associated processes 
    '''

    len_old = len(old) - old.count('')
    len_new = len(new) - new.count('')
    
    if len_old < len_new:
        for port in new:
            if not port in old:
                print 'Port ', port, ' Connected'
                time.sleep(timeout)
                
                asink_index = get_audio_sink_index(audio_sinks[new.index(port)])
                
                if not asink_index == '':
                    print "\t Audio Sink Index: ", asink_index
                    cmd = [get_terminal() + ' -e \'bash -c "python ' +
                              bcp_path + ' ' + port + ' ' + asink_index +
                              '"; bash \'']
                    bcp[port] = subprocess.Popen(cmd,shell=True)
                    time.sleep(timeout)
                    bcp[port] = process_tree(str(bcp[port].pid))
                    print 'PID ', bcp[port]
                    
                else: print "Corresponding Audio Sink not connected !!!"
                
                time.sleep(timeout)

    elif len_old > len_new:
        for port in old:
            if not port in new:
                print 'Port ', port, ' Disconnected'
                if port in bcp:
                    os.system("kill -9 " + bcp[port])
                    bcp.pop(port)
                time.sleep(timeout)
               
                
def get_audio_sink_index(asink):
    ''' Check and return the Index of requested audio sink
    '''

    x = commands.getoutput("pacmd list-sinks | " +
                           "grep -e 'index' -e 'sysfs.path'").split('\n')

    for item in x:
        if 'index' in item:
            index = item.split(':')[1].replace(' ','')
        else:
            if asink in item:
                return index

    return ''                

if __name__ == '__main__':

    # In Rpi to force analog audio instead of 'default' HDMI audio
    os.system("amixer cset numid=3 2")
    time.sleep(timeout)
    
    ports = ['']*len(ttyUSB)

    while True:
        temp_ports = get_ports()
        if not ports == temp_ports:
            print temp_ports
            action_on_ports(ports,temp_ports)
            ports = temp_ports

        time.sleep(timeout)
