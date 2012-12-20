#!/usr/bin/env python

"""
A packet formats.
"""

class SpiNNakerP2PPacket(object):
	
	def __init__(self, system, data, destination, length):
		"""
		data is an arbitary payload
		
		destination is the destination the packet is intended for as a tuple (x, y)
		
		length is the number of bits the packet contains
		"""
		self.system      = system
		self.data        = data
		self.destination = destination
		self.length      = length
		
		# The time-phase in which the packet was created
		self.time_phase = self.system.time_phase
		
		# Add ourselves to the global set of packets
		self.system.packets.append(self)
		
		# Optional meta-data for senders/receivers to fill in
		self.send_time          = None # Time the packet was sent
		self.receive_time       = None # Time the packet was received successfully
		self.source             = None # The position of the node that sent the packet
		self.drop_time          = None # Time the packet was dropped
		self.drop_location      = None # Location where the packet was dropped
		self.emergency_time     = [] # Times the packet was emergency routed
		self.emergency_location = [] # Locations the packet was emergency routed
		
		# Is this packet is being emergency routed?
		self.emergency = False
		
		# The amount of time the packet has been waiting to be forwarded by a router
		self.wait = 0
		
		# The number of hops this packet took to reach its current position
		self.distance = 0
	
	
	def has_expired(self):
		return self.time_phase ^ self.system.time_phase == 0b11

