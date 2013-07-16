#!/usr/bin/python

import datetime, sys

f = open('/mnt/storm/oom.log', 'w')
f.write('Worker %s ran out of memory at %s\n' %(sys.argv[1], str(datetime.datetime.now())))
f.close()

