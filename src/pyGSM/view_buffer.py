import os
import sys
import time

buffer_in = open (sys.argv[1], 'r', os.O_NONBLOCK)
buffer_out = open(sys.argv[2], 'r', os.O_NONBLOCK)

buffer_in.readlines()
buffer_out.readlines()

while True:
	line = buffer_out.readline()
	if line: print('>> ' + line.replace('\n',''))				
	
	line1 = buffer_in.readline()
	if line1: print('<< ' + line1.replace('\n',''))
	
	if not (line and line1): time.sleep(0.1)
