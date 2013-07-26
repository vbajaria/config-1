import os, boto, datetime, socket
from subprocess import Popen, PIPE
from boto.s3.key import Key

AWS_ACCESS_KEY_ID = 'AKIAJZX3DTK5VLHPLE3Q'
AWS_SECRET_ACCESS_KEY = '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'

dt = datetime.date.today() - datetime.timedelta(days=1)
conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
bucket = conn.get_bucket('grepdata-kafka')

for dir, s, files in os.walk('/mnt/data/kafka'):
    for f in files:
        local_filename = '%s/%s' %(dir, f)
        s3_filename = 'REPLACE_WITH_KAFKA_SERVER%s' %local_filename

        local_size  = os.stat(local_filename).st_size
        remote_size = 0

        try:
            remote_size = bucket.lookup(s3_filename).size             

            if local_size == remote_size:
                print '\tSkipping %s (%d kB)' %(local_filename, local_size / 1024)
                continue
        except AttributeError:
            pass
    
        print 'Uploading %s (%d kB)' %(local_filename, (local_size - remote_size) / 1024)

        key = Key(bucket)
        key.key = s3_filename
        key.set_contents_from_filename(local_filename)

