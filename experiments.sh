#!/bin/bash

# Runs the experiments which generated all data used in the paper.
# Executing all these tests takes a long time and I ran it overnight.

NUM_RUNS=20000
W=4
H=4
SOURCE_PROB="0.08"
OTHER_PROB1="0.005"
OTHER_PROB2="0.010"
DEFAULT_LATENCY=$((12+4+4))
# Packet time on unloaded system with no sata link, real and slow variations
echo "$0 $LINENO"
pypy packet_time.py $NUM_RUNS $W $H $SOURCE_PROB 0.0 0
echo "$0 $LINENO"
pypy packet_time.py $NUM_RUNS $W $H $SOURCE_PROB 0.0 $DEFAULT_LATENCY
echo "$0 $LINENO"
pypy packet_time.py $NUM_RUNS $W $H $SOURCE_PROB 0.0 100
# ...on lightly loaded system...
echo "$0 $LINENO"
pypy packet_time.py $NUM_RUNS $W $H $SOURCE_PROB 0.005 0
echo "$0 $LINENO"
pypy packet_time.py $NUM_RUNS $W $H $SOURCE_PROB 0.005 $DEFAULT_LATENCY
echo "$0 $LINENO"
pypy packet_time.py $NUM_RUNS $W $H $SOURCE_PROB 0.005 100
# ...on normally loaded system...
echo "$0 $LINENO"
pypy packet_time.py $NUM_RUNS $W $H $SOURCE_PROB 0.01 0
echo "$0 $LINENO"
pypy packet_time.py $NUM_RUNS $W $H $SOURCE_PROB 0.01 $DEFAULT_LATENCY
echo "$0 $LINENO"
pypy packet_time.py $NUM_RUNS $W $H $SOURCE_PROB 0.01 100


# Packet travel distances (run the six experiments)
NUM_RUNS=20000
W=1
H=1
echo "$0 $LINENO"
pypy packet_drop_areas.py $NUM_RUNS $W $H 0
echo "$0 $LINENO"
pypy packet_drop_areas.py $NUM_RUNS $W $H 1
echo "$0 $LINENO"
pypy packet_drop_areas.py $NUM_RUNS $W $H 2
echo "$0 $LINENO"
pypy packet_drop_areas.py $NUM_RUNS $W $H 3
echo "$0 $LINENO"
pypy packet_drop_areas.py $NUM_RUNS $W $H 4
echo "$0 $LINENO"
pypy packet_drop_areas.py $NUM_RUNS $W $H 5
W=2
H=2
echo "$0 $LINENO"
pypy packet_drop_areas.py $NUM_RUNS $W $H 0
echo "$0 $LINENO"
pypy packet_drop_areas.py $NUM_RUNS $W $H 1
echo "$0 $LINENO"
pypy packet_drop_areas.py $NUM_RUNS $W $H 2
echo "$0 $LINENO"
pypy packet_drop_areas.py $NUM_RUNS $W $H 3
echo "$0 $LINENO"
pypy packet_drop_areas.py $NUM_RUNS $W $H 4
echo "$0 $LINENO"
pypy packet_drop_areas.py $NUM_RUNS $W $H 5
W=4
H=4
echo "$0 $LINENO"
pypy packet_drop_areas.py $NUM_RUNS $W $H 0
echo "$0 $LINENO"
pypy packet_drop_areas.py $NUM_RUNS $W $H 1
echo "$0 $LINENO"
pypy packet_drop_areas.py $NUM_RUNS $W $H 2
echo "$0 $LINENO"
pypy packet_drop_areas.py $NUM_RUNS $W $H 3
echo "$0 $LINENO"
pypy packet_drop_areas.py $NUM_RUNS $W $H 4
echo "$0 $LINENO"
pypy packet_drop_areas.py $NUM_RUNS $W $H 5
