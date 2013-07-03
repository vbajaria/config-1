#!/usr/bin/env python

'''
add a entry in hdfs-site.xml as follows:

<property>
  <name>topology.script.file.name</name>
  <value>/path/to/this/rack_awareness_topology.py</value>
</property>
'''

import sys
from string import join

DEFAULT_RACK = '/default/rack0';

RACK_MAP = { 
		#ephemeral rack
		'ec2-50-17-156-30.compute-1.amazonaws.com' : '/datacenter0/rack0',
                'ip-10-60-146-230.ec2.internal' : '/datacenter0/rack0',
                '10.60.146.230' : '/datacenter0/rack0',

		'ec2-54-242-69-12.compute-1.amazonaws.com' : '/datacenter0/rack0',
                'ip-10-12-158-109.ec2.internal' : '/datacenter0/rack0',
                '10.12.158.109' : '/datacenter0/rack0',

		#ebs rack
		'ec2-54-224-124-211.compute-1.amazonaws.com' : '/datacenter0/rack1',
                'ip-10-60-141-246.ec2.internal' : '/datacenter0/rack1',
                '10.16.141.246' : '/datacenter0/rack1',

		'ec2-23-20-161-167.compute-1.amazonaws.com' : '/datacenter0/rack1',
                'ip-10-84-107-112.ec2.internal' : '/datacenter0/rack1',
                '10.84.107.112' : '/datacenter0/rack1',

                'ec2-184-72-129-122.compute-1.amazonaws.com' : '/datacenter0/rack1',
		'ip-10-119-35-106.ec2.internal' : '/datacenter0/rack1',
                '10.119.35.106' : '/datacenter0/rack1',

                'ec2-107-20-59-12.compute-1.amazonaws.com' : '/datacenter0/rack1',
                'ip-10-218-35-47.ec2.internal' : '/datacenter0/rack1',
                '10.218.35.47' : '/datacenter0/rack1', 
}

if len(sys.argv)==1:
  print DEFAULT_RACK
else:
  print join([RACK_MAP.get(i, DEFAULT_RACK) for i in sys.argv[1:]]," ")
