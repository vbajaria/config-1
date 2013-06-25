import os, boto, datetime
from subprocess import Popen, PIPE
from boto.s3.key import Key

AWS_ACCESS_KEY_ID = 'AKIAJZX3DTK5VLHPLE3Q'
AWS_SECRET_ACCESS_KEY = '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'

ps = 'mysqldump -u root -pntropydb ntropy | gzip -c > /home/ubuntu/dump.gz'
Popen(ps, shell=True).communicate()

conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
bucket = conn.get_bucket('grepdata-mysql')
key = Key(bucket)
key.key = 'dump.gz.%s' %datetime.datetime.now().replace(microsecond=0, second=0).strftime('%Y-%m-%d-%H-%M')
key.set_contents_from_filename('dump.gz')

ps = 'rm /home/ubuntu/dump.gz'
Popen(ps, shell=True).communicate()

