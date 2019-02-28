import os
import time
import fcntl
import threading

class monitor_call_logs(object):

    def __init__(self, path):
        
        self.call_in_log = path+'/call_in_log.txt'
        self.call_wait_log = path+'/call_wait_log.txt'
        self.call_out_log = path+'/call_out_log.txt'
        self.call_wait_queue = path+'/../call_wait_queue.txt'

        self.in_log_size = os.stat(self.call_in_log).st_size
        self.wait_log_size = os.stat(self.call_wait_log).st_size
        self.out_log_size = os.stat(self.call_out_log).st_size
        self.wait_queue_size = os.stat(self.call_wait_queue).st_size

        self.call_to_service = ''

        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True                            # Daemonize thread
        thread.start()                                  # Start the execution

        

    def run(self):
        while True:
            time.sleep(1)
            if os.stat(self.call_in_log).st_size > self.in_log_size:
                time.sleep(1)
                self.manage_call_queues(self.call_in_log)
                self.in_log_size = os.stat(self.call_in_log).st_size 
            if os.stat(self.call_wait_log).st_size > self.wait_log_size:
                time.sleep(1)
                self.manage_call_queues(self.call_wait_log)
                self.wait_log_size = os.stat(self.call_wait_log).st_size 
            if os.stat(self.call_out_log).st_size > self.out_log_size:
                self.call_to_service=''
                time.sleep(1)
                self.manage_call_queues(self.call_out_log)
                self.out_log_size = os.stat(self.call_out_log).st_size 
            if os.stat(self.call_wait_queue).st_size > self.wait_queue_size:
                time.sleep(1)
                if not self.call_to_service: self.wait_to_in()
           
    def manage_call_queues(self,path):
		f = open(path, 'r')
		fcntl.flock(f,fcntl.LOCK_EX)
		numbers = f.readlines()
		fcntl.lockf(f,fcntl.LOCK_UN)
		f.close()
		#print 'Event File = ', numbers
		if numbers:
			if 'call_in' in path:
				print "Pushing in = ", numbers[-1]
				self.push_in_queue(numbers[-1])
			elif 'call_wait' in path:
				self.push_wait_queue(numbers[-1])
			else: 
				self.wait_to_in()

    def push_in_queue(self,number):
	    self.call_to_service = number.replace('\n','')
	    print 'Push in queue = ', self.call_to_service


    def push_wait_queue(self,number):
	    f = open(self.call_wait_queue,'r+w')
	    fcntl.flock(f, fcntl.LOCK_EX)
	    if (number) not in f.readlines():
	    	f.write(number)
	    f.flush()
	    fcntl.flock(f, fcntl.LOCK_UN)
	    f.close()

    def wait_to_in(self):
        f = open(self.call_wait_queue,'r+w')
        fcntl.flock(f, fcntl.LOCK_EX)
        numbers = f.readlines()
        print "Numbers for Wait to in = ", numbers
        if numbers:
            f.truncate(0)
            f.write(''.join(numbers[1:]))
            f.flush()
            ''' 
            f1 = open(folderpath+'dummy.txt','w')
            f1.truncate(0)
            f1.write(''.join(numbers[1:]))
            f1.flush()
            f1.close()
            os.system('rm '+folderpath+'call_wait_queue.txt')
            os.system('mv '+folderpath+'dummy.txt '+folderpath+'call_wait_queue.txt')
            '''
            self.push_in_queue(numbers[0])
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()
        self.wait_queue_size = os.stat(self.call_wait_queue).st_size 
