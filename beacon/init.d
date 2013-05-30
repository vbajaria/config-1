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

case "$2" in
  start)
    START "java -cp /usr/lib/beacon/dataapi-0.1.jar io.ntropy.dataapi.BeaconService server /usr/lib/beacon/$1-config.yml"
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

