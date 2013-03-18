#!/bin/sh

USAGE ()
{
  echo "Usage: $NAME {nimbus|supervisor|ui} {start|stop}" >&2
}

if [ -z $2 ]; then
  USAGE
  exit 1
fi

SERVICE=$1

my_dir=`dirname $0`
. $my_dir/service_config.sh $1

case "$2" in
  start)
    START "/usr/lib/storm/bin/storm $1"
  ;;
  stop)
    STOP "/usr/lib/storm/bin/storm $1"
  ;;
  *)
    USAGE
    exit 1
  ;;
esac

exit 0

~
