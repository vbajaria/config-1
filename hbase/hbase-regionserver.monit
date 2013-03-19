check process regionserver
    matching "regionserver"
    start program = "/usr/lib/hbase/bin/hbase-daemon.sh start regionserver"
    stop program = "/usr/lib/hbase/bin/hbase-daemon.sh stop regionserver"
    if 5 restarts within 5 cycles then timeout
    alert premal@grepdata.com

