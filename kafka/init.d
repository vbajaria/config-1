#!/bin/bash

USAGE ()
{
  echo "Usage: $NAME {start|stop} " >&2
}

case "$1" in
  start)
    /usr/lib/kafka/bin/kafka-server-start.sh /usr/lib/kafka/config/server.properties > /var/log/kafka/access_log 2> /var/log/kafka/error_log
  ;;
  stop)
    /usr/lib/kafka/bin/kafka-server-stop.sh
  ;;
  *)
    USAGE
    exit 1
  ;;
esac

exit 0
