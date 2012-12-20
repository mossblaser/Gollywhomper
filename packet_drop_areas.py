#!/usr/bin/env python

"""
Experiments on a system with normal traffic to see where packets go, how they're
dropped and delayed etc.

This is a mess! Sorry!

usage:

  pypy packet_drop_areas.py [cycles] [width] [height] [exp_no]

cycles is the number of cycles to run for

width and height are the size of the system in 3-board blocks

exp_no is:

0: Run with spinn-links
1: Run with spinn-links without emergency routing
2: Run with slow spinn-links
3: Run with slow spinn-links without emergency routing
4: Run with only silistix links
5: Run with only silistix links without emergency routing

produces results files pda_*.log

"""

import sys

from collections import defaultdict

import model.topology as topology

from experiment import Simulation

class PacketDropAreasExperiment(Simulation):
	"""
	Experiment on the effects of packets 
	"""
	
	def __init__(self, resultfile_prefix = "pda_"):
		Simulation.__init__(self, resultfile_prefix)
	
	
	def measurement_average_packet_distance(self, datafile):
		"""
		Measure the time/hops taken by packets around the network
		"""
		# Set up
		datafile.write("shortest_hops actual_hops time\n")
		
		yield
		
		# Do nothing during the experiment
		try:
			while True:
				yield
		except Simulation.StopExperiment:
			pass
		
		# Collect the results after the experiment
		
		for packet in self.system.packets:
			# All delivered packets
			if packet.receive_time is not None:
				datafile.write("%d %d %d\n"%(
					# Shortest Hops
					topology.manhattan(
						topology.get_path(topology.zero_pad(packet.source),
						                  topology.zero_pad(packet.destination),
						                  (12*Simulation.WIDTH, 12*Simulation.HEIGHT))
					) + 1,
					# Actual Hops
					packet.distance,
					# Time
					packet.receive_time - packet.send_time,
				))
	
	
	def measurement_packet_drop_locations(self, datafile):
		"""
		Measure the time taken for packets emitted from a single core to arrive at
		various destinations. This core is set to broadcast more packets than other
		cores to speed up data collection.
		"""
		# Set up
		datafile.write("#x y"\
		               " packets_routed"\
		               " packet_emergency_routed"\
		               " router_idle_cycles"\
		               " router_blocked_cycles"\
		               " router_packet_timeout"\
		               " generator_injected_packets"\
		               " generator_dropped_packets"\
		               " generator_packets_received"\
		               "\n")
		
		yield
		
		# Do nothing during the experiment
		try:
			while True:
				yield
		except Simulation.StopExperiment:
			pass
		
		# Collect the results after the experiment
		# {(x,y) : (core.counters, router.counters), ...}
		results = {}
		for board in self.torus.boards.itervalues():
			for chip in board.chips.itervalues():
				results[chip.router.mesh_position] = ( chip.traffic_generator.counters
				                                     , chip.router.counters)
		
		# Now create a full datafile which puts something in every position on the
		# possible space
		for y in range(12*Simulation.WIDTH):
			for x in range(12*Simulation.HEIGHT):
				c_counters, r_counters = results[(x,y)]
				datafile.write("%d %d %d %d %d %d %d %d %d %d\n"%(
					# Destination Position
					x, y,
					r_counters["packets_routed"],
					r_counters["packet_emergency_routed"],
					r_counters["router_idle_cycles"],
					r_counters["router_blocked_cycles"],
					r_counters["router_packet_timeout"],
					c_counters["generator_injected_packets"],
					c_counters["generator_dropped_packets"],
					c_counters["generator_packets_received"],
				))
					
			datafile.write("\n");



if __name__=="__main__":
	# Run me with:
	# seq 0 5 | xargs -n1 -P2 time pypy packet_drop_areas.py 10000
	# To execute all four experiments in parallel (on -P[cores] cores).
	
	cycles     = int(sys.argv[1])
	width      = int(sys.argv[2])
	height     = int(sys.argv[3])
	experiment = int(sys.argv[4])
	
	Simulation.WIDTH = width
	Simulation.HEIGHT = height
	
	orig_wait_before_emergency = Simulation.WAIT_BEFORE_EMERGENCY
	orig_wait_before_drop      = Simulation.WAIT_BEFORE_DROP
	
	prefix = "pda_%dsteps_%dx%d_"%(cycles, width, height)
	
	# Run under normal conditions
	def normal():
		Simulation.WAIT_BEFORE_EMERGENCY = orig_wait_before_emergency
		Simulation.WAIT_BEFORE_DROP = orig_wait_before_drop
		Simulation.USE_SATA_LINKS = True
		s = PacketDropAreasExperiment(prefix)
		s.run(cycles)
	
	# Run once without emergency routing
	def normal_no_emergency():
		Simulation.WAIT_BEFORE_EMERGENCY = 1000000
		Simulation.WAIT_BEFORE_DROP = 1000000
		Simulation.USE_SATA_LINKS = True
		s = PacketDropAreasExperiment("%sno_emg_"%prefix)
		s.run(cycles)
	
	# Run with extreme spinn delay
	def extreme():
		Simulation.WAIT_BEFORE_EMERGENCY = orig_wait_before_emergency
		Simulation.WAIT_BEFORE_DROP = orig_wait_before_drop
		Simulation.USE_SATA_LINKS = True
		Simulation.SATA_LATENCY = 200
		Simulation.SATA_BUFFER_LENGTH = 200
		s = PacketDropAreasExperiment("%sextreme_"%prefix)
		s.run(cycles)
	
	# Run once without emergency routing
	def extreme_no_emergency():
		Simulation.WAIT_BEFORE_EMERGENCY = 1000000
		Simulation.WAIT_BEFORE_DROP = 1000000
		Simulation.USE_SATA_LINKS = True
		Simulation.SATA_LATENCY = 200
		Simulation.SATA_BUFFER_LENGTH = 200
		s = PacketDropAreasExperiment("%sextreme_no_emg_"%prefix)
		s.run(cycles)
	
	# Without spinnlinks!
	
	# Run under normal conditions
	def no_spinn():
		Simulation.WAIT_BEFORE_EMERGENCY = orig_wait_before_emergency
		Simulation.WAIT_BEFORE_DROP = orig_wait_before_drop
		Simulation.USE_SATA_LINKS = False
		s = PacketDropAreasExperiment("%sno_spinn_"%prefix)
		s.run(cycles)
	
	# Run once without emergency routing
	def no_spinn_no_emergency():
		Simulation.WAIT_BEFORE_EMERGENCY = 1000000
		Simulation.WAIT_BEFORE_DROP = 1000000
		Simulation.USE_SATA_LINKS = False
		s = PacketDropAreasExperiment("%sno_emg_no_spinn_"%prefix)
		s.run(cycles)
	
	exps = [normal, normal_no_emergency, extreme, extreme_no_emergency, no_spinn, no_spinn_no_emergency]
	exps[experiment]()
