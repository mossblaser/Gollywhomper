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
		
		# Is this packet is being emergency routed?
		self.emergency = False
		
		# The amount of time the packet has been waiting to be forwarded by a router
		self.wait = 0
		
		# The number of hops this packet took to reach its current position
		self.distance = 0
	
	
	def has_expired(self):
		return self.time_phase ^ self.system.time_phase == 0b11

