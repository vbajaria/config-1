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
    JAVAOPTS="-Xmx2048m -Xms512m \
          -XX:+UseParNewGC -XX:+UseConcMarkSweepGC -XX:+CMSParallelRemarkEnabled -verbose:gc -XX:+PrintGCDateStamps -XX:+PrintGCDetails -Xloggc:/var/log/api/$1-gc.log \
          -Dcom.sun.management.jmxremote.port=$JMXPORT \
          -Dcom.sun.management.jmxremote.ssl=false \
          -Dcom.sun.management.jmxremote.authenticate=false \
          -Dcom.sun.management.jmxremote.local.only=false \
          -Dcom.sun.management.jmxremote \
          -Djava.rmi.server.hostname=HOSTNAME"

    START "java $JAVAOPTS -cp /usr/lib/api/dataapi-0.1.jar:/usr/lib/storm/storm-0.9.0-wip16.jar:/usr/lib/storm/lib/*:/usr/lib/storm/conf/ io.ntropy.dataapi.DataApiService server /usr/lib/api/$1-config.yml"
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

