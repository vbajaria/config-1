#!/bin/sh

USAGE ()
{
  echo "Usage: $NAME {api-dev|api-prod|api-prod-https} {start|stop}" >&2
}

if [ -z $2 ]; then
  USAGE
  exit 1
fi

my_dir=`dirname $0`
. $my_dir/service_config.sh

SERVICE=$1
JMXPORT=$3

case "$2" in
  start)
    JAVAOPTS="-Xmx12000m -Xms512m \
          -agentpath:/home/ubuntu/yjp-12.0.5/bin/linux-x86-64/libyjpagent.so=disablestacktelemetry,disableexceptiontelemetry,builtinprobes=none,delay=10000,port=7092 \
          -XX:+UseParNewGC -XX:+UseConcMarkSweepGC -XX:+CMSParallelRemarkEnabled -verbose:gc -XX:+PrintGCDateStamps -XX:+PrintGCDetails -Xloggc:/var/log/api/$1-gc.log"

    START "java $JAVAOPTS -cp /usr/lib/api/dataapi-0.1.jar:/usr/lib/storm/storm-0.9.0-wip16.jar:/usr/lib/storm/lib/*:/usr/lib/storm/conf/:/usr/lib/hadoop/hadoop-core-1.0.4.jar:/usr/lib/hbase/hbase-0.94.9.jar io.ntropy.dataapi.DataApiService server /usr/lib/api/$1-config.yml"
  ;;
  stop)
    STOP 
  ;;
  *)
    USAGE
    exit 1
  ;;
esac

exit 0

