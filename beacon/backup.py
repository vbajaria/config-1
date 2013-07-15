import os, boto, datetime, socket
from subprocess import Popen, PIPE
from boto.s3.key import Key

AWS_ACCESS_KEY_ID = 'AKIAJZX3DTK5VLHPLE3Q'
AWS_SECRET_ACCESS_KEY = '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'

dt = datetime.date.today() - datetime.timedelta(days=1)
conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
bucket = conn.get_bucket('grepdata-logs')

for service in ['', 'https']:
    if service:
        filename = 'access-%s.log.gz' %dt.strftime('%Y-%m-%d')
    else:
        filename = 'access-https-%s.log.gz' %dt.strftime('%Y-%m-%d')
    key = Key(bucket)
    key.key = '%s-%s' %(socket.gethostname().replace('ip-', ''), filename)
    key.set_contents_from_filename('/grepdata/beacon/%s' %filename)

