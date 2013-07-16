#!/usr/bin/python

import datetime, sys

f = open('/mnt/storm/error.log', 'w')
f.write('Worker %s errored out at %s\n' %(sys.argv[1], str(datetime.datetime.now())))
f.close()

