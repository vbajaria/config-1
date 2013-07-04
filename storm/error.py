#!/usr/bin/python

import datetime

f = open('oom.log', 'w')
f.write('Errored out at %s\n' %str(datetime.datetime))
f.close()

