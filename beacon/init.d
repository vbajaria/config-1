#!/bin/sh

USAGE ()
{
  echo "Usage: $NAME {beacon-dev|beacon-prod|beacon-prod-https} {start|stop}" >&2
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
    JAVAOPTS="-Xmx1536m -Xms256m \
          -XX:+UseParNewGC -XX:+UseConcMarkSweepGC -XX:+CMSParallelRemarkEnabled -verbose:gc -XX:+PrintGCDateStamps -XX:+PrintGCDetails -Xloggc:/var/log/beacon/$1-gc.log
          -Dcom.sun.management.jmxremote.port=$JMXPORT \
          -Dcom.sun.management.jmxremote.ssl=false \
          -Dcom.sun.management.jmxremote.authenticate=false \
          -Dcom.sun.management.jmxremote.local.only=false \
          -Dcom.sun.management.jmxremote \
          -Djava.rmi.server.hostname=HOSTNAME"
    START "java $JAVAOPTS -cp /usr/lib/beacon/dataapi-0.1.jar io.ntropy.dataapi.BeaconService server /usr/lib/beacon/$1-config.yml"
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

