Gollywhomper: A SpiNNaker interconnect simulation
=================================================

This is a simulator for playing with the SpiNNaker system, in particular the
effects of off-board interconnection via S-ATA SpiNN-Links.

The model is coded relatively nicely and lives in ./model/. The experiments in
the root were put together in a hurry and do not exhibit quite the same level of
fit and finish.

Usage
-----

For experiment scripts see:

* packet_time.py
* packet_drop_areas.py
* packets_in_transit.py

Take a look in experiments.sh for the values of all experiments used by me in my
write-up.

The staticly defined  values in experiment.py define the basic experimental
parameters used based on conversations with staff in the department.

The name...
-----------

The spinnaker is a sail. A gennaker is a cross between a spinnaker and a genoa
sail. A gollywhomper was an early form of gennaker used in the 1870s. It also
sounds hilarious.
