#!/bin/bash

NAME="./check_and_run.sh"

STORM_CLASSPATH=/usr/lib/storm/storm-recipes-0.1-jar-with-dependencies.jar:/usr/lib/storm/storm-0.9.0-wip16.jar:/usr/lib/storm/lib/*:/usr/lib/storm/conf/:/usr/lib/storm/logback/
JAVA_OPTS="-Dlogback.configurationFile=/usr/lib/storm-0.9.0-wip16/logback/cluster.xml -Dlogfile.name=$1.log"

RECIPE_RUNNER()
{
  RUN io.ntropy.management.RecipeRunner /mnt/storm/logs/recipe-runner
}

RECIPE_MONITOR()
{
  RUN io.ntropy.management.RecipeMonitor /mnt/storm/logs/recipe-monitor
}

RECIPE_KILLER()
{
  RUN io.ntropy.management.RecipeKiller /mnt/storm/logs/recipe-killer
}

UPDATE_DIMENSION_CARDINALITY()
{
  RUN io.ntropy.management.UpdateDimensionCardinality /mnt/storm/logs/recipe-update-cardinality
}

POPULATE_BASELINE_DIMENSIONS()
{
  RUN io.ntropy.management.PopulateBaselineDimensions /mnt/storm/logs/recipe-populate-baseline
}

RUN() {
  java $JAVA_OPTS -Dstorm.conf.file=storm.yaml -cp $STORM_CLASSPATH $1 >> $2
}

USAGE()
{
  echo "Usage: $NAME {RecipeRunner|RecipeMonitor|RecipeKiller|UpdateDimensionCardinality|PopulateBaselineDimensions}" >&2
}

if [ -z $1 ]; then
  USAGE
  exit 1
fi

echo "check_and_run: $1"
RUNNING=`ps aux | grep $1 | grep -v grep | grep -v check_and_run | wc -l`

if [ $RUNNING -ne 0 ]; then
  #process is already running
  echo "process $1 is already running. exiting."
  exit 1
fi

case "$1" in
  RecipeRunner)
    RECIPE_RUNNER
  ;;
  RecipeMonitor)
    RECIPE_MONITOR
  ;;
  RecipeKiller)
    RECIPE_KILLER
  ;;
  UpdateDimensionCardinality)
    UPDATE_DIMENSION_CARDINALITY
  ;;
  PopulateBaselineDimensions)
    POPULATE_BASELINE_DIMENSIONS
  ;;
  *)
    USAGE
    exit 1
  ;;
esac
