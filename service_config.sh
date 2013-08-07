#!/bin/bash
# first argument must be a name

if [ -z $1 ]; then
  echo "must supply a name as the first argument"
  exit 1
else
  NAME="$1"
fi

LOG_BASE_DIR=/var/log/service
NOW=$(date +"%Y-%m-%d")
LOG_FILE=$LOG_BASE_DIR/$NAME.$NOW.log

PID_DIR=/var/service/pids
PID_FILE=$PID_DIR/$NAME.pid

LOG_MSG ()
{
  if [ -t 0 ]; then
      echo $1 >> $LOG_FILE
  else
      while read -r text; do
          echo $text >> $LOG_FILE
      done
  fi
}

START ()
{
  if [ -f $PID_FILE ]; then
    if kill -0 `cat $PID_FILE` > /dev/null 2>&1; then
      echo $command running as process `cat $PID_FILE`.  Stop it first.
      exit 1
    fi
  fi
  
  $1 >> $LOG_FILE 2>&1 &
  #($1 2>&1 | LOG_MSG) &
  echo $! > $PID_FILE
  echo running $1 as process `cat $PID_FILE`
  echo logging to $LOG_FILE
}

STOP ()
{
  if [ -f $PID_FILE ]; then
    if kill -0 `cat $PID_FILE` > /dev/null 2>&1; then
      echo stopping $NAME
      kill -9 `cat $PID_FILE`
      echo stopped $NAME
    else
      echo no $NAME to stop
    fi
  else
    echo no $NAME to stop
  fi
}

