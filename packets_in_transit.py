#!/usr/bin/env python

"""
An experiment which sees how many packets are in transit at each cycle of the
simulation.

This is a mess! Sorry!

usage:

  pypy packets_in_transit.py

(no arguments)

produces files pit_*.log

"""

from collections import defaultdict

import model.topology as topology

from experiment import Simulation

class PacketsInTransitExperiment(Simulation):
	"""
	Just a place to put the packets in-transit experiment...
	"""
	
	def __init__(self, resultfile_prefix = "pit_"):
		Simulation.__init__(self, resultfile_prefix)
	
	
	def measurement_packets_in_transit(self, datafile):
		"""
		Measure the number of packets in the system
		"""
		# Set up
		datafile.write("#clock"\
		               " generator_injected_packets"\
		               " generator_dropped_packets"\
		               " generator_packets_received\n") 
		
		all_cores_counters = []
		for board in self.torus.boards.itervalues():
			for chip in board.chips.itervalues():
				all_cores_counters.append(chip.traffic_generator.counters)
		
		yield
		
		# Measure the number of packets about once every clock cycle
		try:
			while True:
				if (yield):
					datafile.write("%d %d %d %d\n"%(
						self.scheduler.clock,
						sum(c["generator_injected_packets"] for c in all_cores_counters),
						sum(c["generator_dropped_packets"] for c in all_cores_counters),
						sum(c["generator_packets_received"] for c in all_cores_counters),
					))
		except Simulation.StopExperiment:
			pass
			# Nothing to write at the end of simulation



if __name__=="__main__":
	s = PacketsInTransitExperiment()
	s.run(10000)

