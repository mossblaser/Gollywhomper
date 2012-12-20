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
		Peek at the packet which could be received.
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
	A link which sends and acknowledges every packet. Packets are received before
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
		
		ack_cycles is the number of cycles it takes after an ack is received for the
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
	A link which buffers up values to be sent. Note this link allows packets to be
	sent and then received in the same cycle!
	"""
	
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



class DelayLineLink(Link):
	"""
	Models a delay-line link which simply introduces latency to a stream of
	packets. The link receives packets and only allows them to be received after a
	certain delay has elapsed. This link may allow multiple packets to be sent and
	recieved per cycle.
	"""
	
	def __init__(self, scheduler, latency):
		"""
		latency is the number of cycles between a packet being sent and it arriving.
		"""
		self.scheduler = scheduler
		self.latency   = latency
		
		# A buffer of [packet, cycles_until_received] pairs
		self.packet_buffer = []
		
		# Start the decrementer running
		self.scheduler.do_later(self.decrement_counters, 1)
	
	
	def decrement_counters(self):
		"""
		Decrement the latency counters on all packets
		"""
		# Make a local copy of the packet buffer (so that we can know what elements
		# are in the buffer "right now")
		packet_buffer_copy = self.packet_buffer[:]
		
		# At the end of the cycle, decrement all these counters
		def later():
			for pair in packet_buffer_copy:
				pair[1] -= 1
		self.scheduler.do_later(later)
		
		# Reschedule the decrementer
		self.scheduler.do_later(self.decrement_counters, 1)
	
	
	def can_send(self):
		# No bandwidth limits
		return True
	
	
	def send(self, data):
		# Add the packet to the buffer at the end of the cycle (so its latency
		# counter isn't decremented until the next cycle).
		def later():
			self.packet_buffer.append([data, self.latency])
		self.scheduler.do_later(later)
	
	
	def can_receive(self):
		# Is there anything in the buffer and has the counter reached zero for the
		# first entry?
		return self.packet_buffer and self.packet_buffer[0][1] <= 0
	
	
	def receive(self):
		assert(self.can_receive())
		packet, _ = self.packet_buffer.pop(0)
		return packet
	
	
	def peek(self):
		assert(self.can_receive())
		packet, _ = self.packet_buffer[0]
		return packet



class SATALink(Link):
	"""
	A link which models the inter-board links used on spinnaker.
	
	The real device consists of a set of incoming SilistixLink to an FPGA which
	queues up packets and sends them multiplexed over a S-ATA link to another
	board. The FPGA on this board demultiplexes the packets and occasionally sends
	an acknowledgement which allows the sender to mark data as sent and accept
	further packets.
	
	Unlike the "real thing" this link is not bidirectional. A real link should be
	modelled by a pair of these models.
	
	This links is simplistically modelled by being high bandwidth and multiplexed
	with high-latency. This is implemented as follows: The link accepts input and
	produces output via SilistixLinks. The S-ATA link is modelled by num_channels
	delay-lines which are fed at a rate representative of the channel's overall
	bandwidth. Packets are then removed from the delay lines (again at a rate
	representative of the bandwidth) and fed into the appropriate SilistixLink at
	the receiving end.
	
	This model does not account for link errors and acknowledgements (except
	indirectly if generous latency specifications are given).
	"""
	
	def __init__( self
	            , scheduler
	            , num_channels
	            , sata_accept_period
	            , sata_buffer_length
	            , sata_latency
	            , silistix_send_cycles
	            , silistix_ack_cycles
	            ):
		"""
		num_channels is the number of channels supported by the link.
		
		sata_accept_period is the number of cycles between a single packet being
		sent down the link and another packet being allowed to be sent. This is also
		the maximum rate at which packets will be received at the opposite end. This
		delay is multiplied by the size of a packet so larger packets result in a
		longer delay before the next packet arrives.
		
		sata_buffer_length is the number of packets per channel which can be
		buffered in the system.
		
		sata_latency is the number of cycles it takes for a packet to travel down
		a delay line.
		
		silistix_send_cycles see SilistixLink.
		
		silistix_ack_cycles see SilistixLink.
		"""
		
		self.scheduler          = scheduler
		self.num_channels       = num_channels
		self.sata_accept_period = sata_accept_period
		self.sata_buffer_length = sata_buffer_length
		
		# The input and output from which the last packet was successfully
		# sent/received
		self.last_input = 0
		self.last_output = 0
		
		# Create the external links and delay links for all the channels
		self.in_links    = []
		self.out_links   = []
		self.delay_links = []
		# Also initialise a credit counter for each channel which essentially
		# enforces the buffer size limit
		self.credit = []
		for channel in range(self.num_channels):
			self.in_links.append(SilistixLink( self.scheduler
			                                 , silistix_send_cycles
			                                 , silistix_ack_cycles
			                                 ))
			self.out_links.append(SilistixLink( self.scheduler
			                                  , silistix_send_cycles
			                                  , silistix_ack_cycles
			                                  ))
			self.delay_links.append(DelayLineLink( self.scheduler
			                                     , sata_latency
			                                     ))
			self.credit.append(self.sata_buffer_length)
		
		# Schedule the input and output handler routine
		self.scheduler.do_later(self.handler, self.sata_accept_period)
	
	
	def handler(self):
		"""
		Handles up to one incoming packet and one outgoing per call.
		"""
		
		# Try and handle an output starting with the output after the last handled
		# output (round-robin style)
		for channel_num in ((cn+self.last_output+1)%self.num_channels
		                    for cn in xrange(self.num_channels)):
			# Try and find a channel we can receive on which hasn't filled up its
			# buffer
			if self.delay_links[channel_num].can_receive() \
			   and self.out_links[channel_num].can_send():
				# Take the packet out of the delay link and send it out to the world
				self.out_links[channel_num].send(self.delay_links[channel_num].receive())
				
				# Increment the credit counter
				self.credit[channel_num] += 1
				# Note which channel this was for next time
				self.last_output = channel_num
				break
		
		# Try and handle an input starting with the input after the last handled
		# input (round-robin style)
		for channel_num in ((cn+self.last_input+1)%self.num_channels
		                    for cn in xrange(self.num_channels)):
			# Try and find a channel we can receive on which hasn't filled up its
			# buffer
			if self.credit[channel_num] >= 0 \
			   and self.in_links[channel_num].can_receive():
				# Put the packet in the send buffer
				assert(self.delay_links[channel_num].can_send())
				self.delay_links[channel_num].send(self.in_links[channel_num].receive())
				
				# Decrement the credit counter
				self.credit[channel_num] -= 1
				# Note which channel this was for next time
				self.last_input = channel_num
				break
		
		# Reschedule
		self.scheduler.do_later(self.handler, self.sata_accept_period)
	
	
	class SATALinkProxy(Link):
		"""
		A proxy class which allows link-style access to a single channel of the
		SATALink.
		"""
		
		def __init__(self, sata_link, channel_num):
			self.sata_link   = sata_link
			self.channel_num = channel_num
		
		
		def can_send(self):
			return self.sata_link.in_links[self.channel_num].can_send()
		
		
		def send(self, data):
			self.sata_link.in_links[self.channel_num].send(data)
		
		
		def can_receive(self):
			return self.sata_link.out_links[self.channel_num].can_receive()
		
		
		def receive(self):
			return self.sata_link.out_links[self.channel_num].receive()
		
		
		def peek(self):
			return self.sata_link.out_links[self.channel_num].peek()
	
	
	def get_channel_link(self, channel_num):
		"""
		Get a Link-style proxy object which allows transparent access to a single
		channel within the link.
		"""
		assert(0 <= channel_num < self.num_channels)
		return SATALink.SATALinkProxy(self, channel_num)
