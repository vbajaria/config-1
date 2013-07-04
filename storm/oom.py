#!/usr/bin/python

import datetime

f = open('oom.log', 'w')
f.write('Got OOM at %s\n' %str(datetime.datetime))
f.close()

