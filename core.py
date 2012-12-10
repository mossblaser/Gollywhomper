#!/usr/bin/env python

"""
Processor core models.
"""

from random import random
from random import randint
from random import normalvariate

from packet import SpiNNakerP2PPacket

class SpiNNakerTrafficGenerator(object):
	"""
	A simple traffic generator which generates traffic a random intervals and
	receives and discards incoming packets. This is designed to act on behalf of
	the 18 cores which make up a single SpiNNaker chip/node.
	
	All packets sent are 40 bits long and their payload is a reference to this
	object.
	"""
	
	PACKET_LENGTH = 40
	
	def __init__( self
	            , scheduler
	            , system
	            , clock_period
	            , packet_prob
	            , injection_link
	            , exit_link
	            , mesh_dimensions
	            , mesh_position = None
	            , distance_std = None
	            ):
		"""
		clock_period is the number of scheduler ticks per clock cycle.
		
		packet_prob is the probability of a packet being generated each cycle.
		
		injection_link is the link into which packets will be injected by the
		generator.
		
		exit_link is the link through which new packets are received.
		
		mesh_dimensions is the size of the mesh the node is in, tuple(x,y).
		
		mesh_position is the position of the node within the mesh, tuple(x,y) only
		required if distance_std is not None.
		
		distance_std is the standard deviation of the distance along the X and Y
		axes from the node a packet should be delivered. If None then a uniform
		distribution will be used.
		"""
		
		self.scheduler = scheduler
		self.system    = system
		
		self.clock_period = clock_period
		self.packet_prob  = packet_prob
		
		self.injection_link = injection_link
		self.exit_link      = exit_link
		
		self.mesh_dimensions = mesh_dimensions
		self.mesh_position   = mesh_position
		self.distance_std    = distance_std
		
		# Statistic counters
		self.counters = {
			# Number of packets which were successfully injected
			"generator_injected_packets" : 0,
			
			# Number of packets dropped due to injection link congestion
			"generator_dropped_packets" : 0,
			
			# Number of packets received (and ignored)
			"generator_packets_received" : 0,
			
			# Number of cycles executed
			"generator_cycles" : 0,
		}
		
		# Start the generator transmitting
		self.scheduler.do_later(self.tick, self.clock_period)
	
	
	def tick(self):
		"""
		Perform a single CPU tick.
		"""
		
		self.counters["generator_cycles"] += 1
		
		# Absorb any packets sent to us.
		while self.exit_link.can_receive():
			packet = self.exit_link.receive()
			self.counters["generator_packets_received"] += 1
		
		# Possibly send a packet out
		if random() < self.packet_prob:
			if not self.injection_link.can_send():
				# Can't send so we must drop the packet!
				self.counters["generator_dropped_packets"] += 1
			else:
				# Can send, generate a packet and send it!
				
				# Select the packet destination
				if self.distance_std is None:
					# Uniform distribution
					dest = tuple(randint(0, dimension-1) for dimension in self.mesh_dimensions)
				else:
					# Normal distribution
					dest = tuple(int(normalvariate(position, self.distance_std)) % dimension
					             for position, dimension
					             in zip(self.mesh_position, self.mesh_dimensions))
				
				# Send a packet with a reference to this object as a payload and the given
				# destination.
				packet = SpiNNakerP2PPacket(self.system, self, dest,
				                            SpiNNakerTrafficGenerator.PACKET_LENGTH)
				self.injection_link.send(packet)
				self.counters["generator_injected_packets"] += 1
		
		# Schedule the next tick
		self.scheduler.do_later(self.tick, self.clock_period)
