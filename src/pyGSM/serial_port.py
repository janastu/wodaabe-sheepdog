#import sys             ### to detect the USB Serial port
import serial           ### the serial port library
import os               ### for getting current working directory
import threading
import commands         ### to get output of a bash command
import subprocess       ### to view serial buffer


''' The serial port object that has access to buffer files '''
class port(object):
    
    def __init__(self, port, buffer_path='.'):
        ### Open files in non-blocking mode to be accessed by serial port and 
        ### other objects
        self.viewbuffpid = None    
        self.buffer_in = None
        self.buffer_out = None

        try:
            self.usb = serial.Serial('/dev'+'/'+port, timeout=0.1)
        except:
            print('Device Not Connected!!!')
            exit()

        try:
            os.makedirs(buffer_path + '/' + port)
        except OSError:
            if not os.path.isdir(buffer_path + '/' + port): raise


        self.buffer_in_filename = buffer_path + '/' + port + '/in_buffer'
        self.buffer_out_filename = buffer_path + '/' + port + '/out_buffer'

        self.buffer_in = open (self.buffer_in_filename, 'a+', os.O_NONBLOCK)
        self.buffer_out = open(self.buffer_out_filename, 'a+', os.O_NONBLOCK)    

        ### Ignore the previous contents of buffer file
        self.buffer_in.readlines()
        #self.buffer_out.readlines()

        ### Get terminal software in system
        terminal_soft = commands.getoutput("echo $TERM")
        self.viewbuffpid = subprocess.Popen([terminal_soft, '-e', 'python', os.path.split(os.path.realpath(__file__))[0]+'/view_buffer.py',     self.buffer_in_filename, self.buffer_out_filename])

        self.thread = threading.Thread(target=self.run, args=())
        self.thread.daemon = True                            # Daemonize thread
        self.thread.start()                                  # Start the execution
        
    def __del__(self):
        ### While object being deleted, disconnect call 
        self.viewbuffpid.kill()

    def run(self):
        ### In infinite loop, do two tasks
        ### 1. Check output buffer file, and send it out through serial port
        ### 2. Read data from serial port, if any, and save it in buffer files
        
        buffer_in = open (self.buffer_in_filename, 'a+', os.O_NONBLOCK)
        buffer_out = open(self.buffer_out_filename, 'a+', os.O_NONBLOCK)
        buffer_out.readlines()

        while True:
            line = buffer_out.readline()
            if line: self.usb.write(line)
    
            line = self.usb.readline().replace('\r\n','')
            if line:
                buffer_in.write(line)
                buffer_in.write('\n')
                buffer_in.flush()
        
    ### To write to output buffer file
    def write(self,line):
        self.buffer_out.write(line)
        self.buffer_out.flush()
    
    ### To read from input buffer file
    def readline(self):
        return self.buffer_in.readline()

    ### Close files in destructor
    def __del__(self):
        print "Destructor called"
        self.viewbuffpid.kill()        
        if self.buffer_in: self.buffer_in.close()
        if self.buffer_out:    self.buffer_out.close()
        self.thread.join()
        
    
if __name__ == '__main__':

    ports = commands.getoutput('ls /dev/ | grep ttyUSB')
    if not ports: 
        print('NO Serial Port Connected !!!')    
        exit()
    ports = ports.split('\n')
    
    use_port = 0
    if len(ports) > 1:
        for index, item  in enumerate(ports):
            print (index, item)
        use_port = input('Enter INDEX of the Port to use - ')
    
    usb = port(ports[use_port])
    
    while True:    
        usb.write(raw_input()+'\n')    

