#!/usr/bin/env python

"""
Run experiments with systems where the latency of packets from a single source
are measured.

This is a mess! Sorry!

usage:

  pypy packet_time.py [steps] [width] [height] [source_rate] [other_rate] [sata_latency]

steps is the number of cycles to simulate

width height are the size of the system in 3-board units

source-rate is the rate at which the source sends packets

other_rate is the rate at which all other nodes send packets

sata_latency is the number of cyclces the sata link takes to send packets. If
zero, silistix links are used instead.
"""


from collections import defaultdict

from random import shuffle

from itertools import product

import model.topology as topology

from experiment import Simulation

class PacketTimeExperiment(Simulation):
	"""
	Experiment on the effects of packets 
	"""
	
	def __init__(self
	            , source_node
	            , source_packet_prob
	            , other_packet_prob
	            , resultfile_prefix = "pte_"
	            ):
		self.source_node        = source_node
		self.source_packet_prob = source_packet_prob
		self.other_packet_prob  = other_packet_prob
		
		Simulation.__init__(self, resultfile_prefix)
	
	
	def measurement_packets_from_single_source(self, datafile):
		"""
		Measure the time taken for packets emitted from a single core to arrive at
		various destinations. This core is set to broadcast more packets than other
		cores to speed up data collection.
		"""
		# Set up
		datafile.write("#x y shortest_path"\
		               " distance distance_min distance_max"\
		               " time time_min time_max\n")
		
		# A generator which yields random locations in the grid but ensures every
		# location is hit
		def generate_packets():
			locations = list(product(range(12*self.WIDTH), range(12*self.HEIGHT)))
			while True:
				shuffle(locations)
				for location in locations:
					yield location
		packet_gen = generate_packets()
		
		# Set the packet generator rates
		for board in self.torus.boards.itervalues():
			for chip in board.chips.itervalues():
				if chip.traffic_generator.mesh_position == self.source_node:
					chip.traffic_generator.packet_prob = self.source_packet_prob
					chip.traffic_generator.get_random_dest = packet_gen.next
				else:
					chip.traffic_generator.packet_prob = self.other_packet_prob
		
		yield
		
		# Do nothing during the experiment
		try:
			while True:
				yield
		except Simulation.StopExperiment:
			pass
		
		# Collect the results after the experiment
		
		# Create a dictionary {(x,y) : [(distance, time),...], ...} which will store
		# the results for all packets from our source node
		destinations = defaultdict(list)
		for packet in self.system.packets:
			if packet.source == self.source_node and packet.receive_time is not None:
				# A packet from the node which actually arrived
				destinations[packet.destination].append(
					(packet.distance, packet.receive_time - packet.send_time))
		
		# Now create a full datafile which puts something in every position on the
		# possible space
		for y in range(12*Simulation.WIDTH):
			for x in range(12*Simulation.HEIGHT):
				if (x,y) in destinations:
					data = destinations[(x,y)]
					datafile.write("%d %d %d %d %d %d %d %d %d\n"%(
						# Destination Position
						x, y,
						# Shortest path
						topology.manhattan(
							topology.get_path(topology.zero_pad(self.source_node),
							                  topology.zero_pad((x,y)),
							                  (12*Simulation.WIDTH, 12*Simulation.HEIGHT))
						),
						# Distance
						sum(d[0] for d in data)/len(data),
						min(d[0] for d in data),
						max(d[0] for d in data),
						# Time
						sum(d[1] for d in data)/len(data),
						min(d[1] for d in data),
						max(d[1] for d in data),
					))
				else:
					# Missing data
					datafile.write("%d %d %d %d %d %d %d %d %d\n"%(
						# Destination Position
						x, y,
						# Shortest path
						topology.manhattan(
							topology.get_path(topology.zero_pad(self.source_node),
							                  topology.zero_pad((x,y)),
							                  (12*Simulation.WIDTH, 12*Simulation.HEIGHT))
						),
						# Distance
						-1,-1,-1,
						# Time
						-1,-1,-1,
					))
					
			datafile.write("\n");



if __name__=="__main__":
	# Usage:
	# pypy packet_time.py [steps] [width] [height] [source_rate] [other_rate] [sata_latency]
	import sys
	sys.argv.pop(0)
	
	steps             = int(sys.argv.pop(0))
	
	Simulation.WIDTH  = int(sys.argv.pop(0))
	Simulation.HEIGHT = int(sys.argv.pop(0))
	
	source_packet_prob = float(sys.argv.pop(0))
	other_packet_prob = float(sys.argv.pop(0))
	
	Simulation.SATA_LATENCY = int(sys.argv.pop(0))
	Simulation.SATA_BUFFER_LENGTH = Simulation.SATA_LATENCY
	
	if Simulation.SATA_LATENCY == 0:
		Simulation.USE_SATA_LINKS = False
	
	prefix = "pte_%dsteps_%dx%d_%0.3fsr_%0.3for_%dsl_"%(
		steps, Simulation.WIDTH, Simulation.HEIGHT, source_packet_prob,
		other_packet_prob,Simulation.SATA_LATENCY
	)
	
	s = PacketTimeExperiment(((12*Simulation.WIDTH)/2,(12*Simulation.HEIGHT)/2),
	                         source_packet_prob, other_packet_prob,
	                         prefix)
	s.run(steps)
