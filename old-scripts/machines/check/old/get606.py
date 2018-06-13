#!/usr/bin/python

import sys
import socket

local = socket.gethostname().split(".")[0]
hosts = local
count = 1

for line in sys.stdin:
	line = line.strip()
	
	ip, name, loc, stuff = line.split(",",3)
	if loc == "606":
		if name != local:
			hosts += "," + name
			count += 1

#Get all the names, and print count (77 in total)
#print(hosts)
#print(count)

#Print a .sh script to check map
for h in hosts.split(","):
	print("echo \"{0} {1}\"".format("Checking:",h))
	print("ssh {0} who".format(h))