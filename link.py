#!/usr/bin/env python

"""
Models of various types of link. The links are able to send Packet objects.
"""

class Link(object):
	"""
	Base class for a Link.
	"""
	
	def __init__(self, scheduler):
		self.scheduler = scheduler
	
	
	def can_send(self):
		"""
		Returns a bool: Can a value be sent down the link?
		"""
		raise NotImplementedError()
	
	
	def send(self, data):
		"""
		Send a packet down the link. Should only be called if can_send() returns
		True.
		"""
		raise NotImplementedError()
	
	
	def can_receive(self):
		"""
		Returns a bool: Is there a value that can be accepted?
		"""
		raise NotImplementedError()
	
	
	def receive(self):
		"""
		Accept a packet from the link. Should only be called if can_receive returns
		true.
		"""
		raise NotImplementedError()
	
	
	def peek(self):
		"""
		Peek at the packet which could be recieved.
		"""
		raise NotImplementedError()



class DeadLink(Link):
	"""
	A broken link.
	"""
	
	def can_send(self):    return False
	def can_receive(self): return False



class SilistixLink(Link):
	"""
	A link which sends and acknowledges every packet. Packets are recieved before
	they are acknowledged.
	"""
	
	READY   = 0
	SENDING = 1
	STABLE  = 2
	ACKING  = 4
	
	def __init__(self, scheduler, send_cycles, ack_cycles):
		"""
		send_cycles is the number of cycles it takes for the data to arrive at the
		reciever (i.e. how long until can_receive will become true).
		
		ack_cycles is the number of cycles it takes after an ack is recieved for the
		link to become ready again.
		"""
		Link.__init__(self, scheduler)
		
		self.send_cycles = send_cycles
		self.ack_cycles  = ack_cycles
		
		# State of the link
		self.state = SilistixLink.READY
		
		# Current packet being sent
		self.cur_packet = None
	
	
	def can_send(self):
		return self.state == SilistixLink.READY
	
	
	def send(self, data):
		assert(self.state == SilistixLink.READY)
		
		self.cur_packet = data
		self.state = SilistixLink.SENDING
		
		def arrived():
			self.state = SilistixLink.STABLE
		
		self.scheduler.do_later(arrived,
		                        self.send_cycles * data.length
		                        + self.ack_cycles * (data.length-1))
	
	
	def can_receive(self):
		return self.state == SilistixLink.STABLE
	
	
	def receive(self):
		assert(self.state == SilistixLink.STABLE)
		
		self.state = SilistixLink.ACKING
		
		def acked():
			self.cur_packet = None
			self.state = SilistixLink.READY
		
		self.scheduler.do_later(acked, self.ack_cycles)
		
		return self.cur_packet
	
	
	def peek(self):
		assert(self.state == SilistixLink.STABLE)
		
		return self.cur_packet



class BufferLink(Link):
	"""
	A link which buffers up values to be sent
	"""
	
	READY   = 0
	SENDING = 1
	STABLE  = 2
	ACKING  = 4
	
	def __init__(self, scheduler, buffer_length = None):
		"""
		buffer_length is the number of entries that can fit in the buffer. None
		means unlimited
		"""
		Link.__init__(self, scheduler)
		
		self.buffer_length  = buffer_length
		
		# The buffer
		self.packet_buffer = []
	
	
	def can_send(self):
		return self.buffer_length is None or len(self.packet_buffer) < self.buffer_length
	
	
	def send(self, data):
		assert(self.can_send())
		
		self.packet_buffer.append(data)
	
	
	def can_receive(self):
		return len(self.packet_buffer) >= 1
	
	
	def receive(self):
		assert(self.can_receive())
		
		return self.packet_buffer.pop(0)
	
	
	def peek(self):
		assert(self.can_receive())
		
		return self.packet_buffer[0]
