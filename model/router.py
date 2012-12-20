#!/usr/bin/env python

"""
A model of a SpiNNaker style router.
"""

import topology


class SpiNNakerRouter(object):
	"""
	A SpiNNaker router arranged in a toroidal, hexagonal mesh. This uses the
	addressing scheme suggested in
	
	Addressing and Routing in Hexagonal Networks with Applications for Tracking
	Mobile Users and Connection Rerouting in Cellular Networks by Nocetti et. al.
	
	With the "z" dimension omitted (and assumed to be zero). X points from
	left-to-right, Y points from bottom-to-top and Z points from
	top-right-to-bottom-left.
	"""
	
	def __init__( self
	            , scheduler
	            , system
	            , injection_link
	            , exit_link
	            , in_links
	            , out_links
	            , period
	            , wait_before_emergency
	            , wait_before_drop
	            ):
		"""
		injection_link is a link from which new packets are being issued by the local
		cores.
		
		exit_link is the link down which packets targeted at this router arrive
		
		in_links is a list [E, NE, N, W, SW, S] of inbound links. This is always
		accessed by reference.
		
		out_links is a list [E, NE, N, W, SW, S] of outbound links. This is always
		accessed by reference.
		
		period is the number of cycles between each routing step.
		
		wait_before_emergency is the number of cycles to wait before trying
		emergency routing
		
		wait_before_drop is the number of cycles to wait before dropping a packet
		which couldn't be sent via the emergency route
		"""
		self.scheduler = scheduler
		self.system    = system
		
		self.injection_link = injection_link
		self.exit_link      = exit_link
		self.in_links       = in_links
		self.out_links      = out_links
		
		self.period                = period
		self.wait_before_emergency = wait_before_emergency
		self.wait_before_drop      = wait_before_drop
		
		# The only chip in a one chip system
		self.mesh_dimensions = (1,1)
		self.mesh_position   = (0,0)
		
		
		# Stat counters
		self.counters = {
			# A packet whose timestamp was too old was dropped
			"timestamp_packet_timeout" : 0,
			
			# A packet was in the router too long and was dropped
			"router_packet_timeout" : 0,
			
			# A packet was forwarded successfully
			"packets_routed" : 0,
			
			# A packet was forwarded successfully via an emergency route
			"packet_emergency_routed" : 0,
			
			# The number of cycles executed by the router
			"router_cycles" : 0,
			
			# The number of cycles the router didn't have any packets to route
			"router_idle_cycles" : 0,
			
			# The number of times packets were available but none could be routed.
			"router_blocked_cycles" : 0,
		}
		
		# A counter which is used to select the first input port to service. This is
		# cycled to achieve a round-robin priority system
		self.first_link = 0
		
		# Schedule the routing step
		self.scheduler.do_later(self.do_route, self.period)
	
	
	def set_mesh_dimensions(self, w, h):
		"""
		Set the size of the mesh this router is part of.
		"""
		self.mesh_dimensions = (w,h)
	
	
	def set_mesh_position(self, x, y):
		"""
		Set the X and Y coordinates of the system the router is part of.
		"""
		self.mesh_position = (x,y)
	
	
	def get_mesh_position(self):
		"""
		Get the X and Y coordinates of the system the router is part of.
		"""
		return self.mesh_position
	
	
	def do_route(self):
		"""
		Perform a single cycle of router activity.
		"""
		
		# Clear out any expired packets
		self.discard_expired_packets()
		
		# A flag that indicates that no incoming packets were available
		idle = True
		
		# A flag that indicates that at least one packet was forwarded
		blocked = True
		
		# Try to service the input buffers
		for src_link in self.links_in_service_order():
			if src_link.can_receive():
				idle = False
				
				packet = src_link.peek()
				packet.wait += 1
				
				# Get the direction that the packet came from
				in_dir = self.in_links.index(src_link) if src_link in self.in_links else None
				
				# Get the destination link of a packet
				dst_link, emg_link = self.get_packet_destination(src_link.peek(), in_dir)
				
				if dst_link.can_send():
					# Forward the packet if the destination is free
					packet.distance += 1
					packet.wait      = 0
					packet.emergency = False
					dst_link.send(src_link.receive())
					self.counters["packets_routed"] += 1
					
					blocked = False
					
				elif packet.wait > self.wait_before_emergency \
				     and emg_link != dst_link \
				     and emg_link.can_send():
					# If the packet has been here long enough, try emergency routing
					packet.distance += 1
					packet.wait      = 0
					packet.emergency = True
					packet.emergency_time.append(self.scheduler.clock)
					packet.emergency_location.append(self.mesh_position)
					# Send the packet via emergency route
					emg_link.send(src_link.receive())
					self.counters["packet_emergency_routed"] += 1
					
					blocked = False
		
		# General counters
		self.counters["router_cycles"] += 1
		if idle:
			self.counters["router_idle_cycles"] += 1
		if not idle and blocked:
			self.counters["router_blocked_cycles"] += 1
		
		# Schedule the next routing step
		self.scheduler.do_later(self.do_route, self.period)
	
	
	def discard_expired_packets(self):
		"""
		Discard any incoming packets which have expired.
		"""
		
		for link in self.in_links + [self.injection_link]:
			while link.can_receive():
				if link.peek().has_expired():
					# The timestamp is too old
					self.counters["timestamp_packet_timeout"] += 1
				elif link.peek().wait > self.wait_before_drop:
					# The packet has been in the router too long
					self.counters["router_packet_timeout"] += 1
				else:
					# The packet shouldn't be expired
					break
				
				# Get rid of it from the queue
				packet = link.receive()
				packet.drop_time = self.scheduler.clock
				packet.drop_location = self.mesh_position
	
	
	def links_in_service_order(self):
		"""
		Returns the links in the order in which they should be serviced
		"""
		links = self.in_links + [self.injection_link]
		
		# Rotate the link list
		ordered_links = links[self.first_link:] + links[:self.first_link]
		
		# Increment the first link counter
		self.first_link = (self.first_link + 1) % len(links)
		
		return ordered_links
	
	
	def get_packet_destination(self, packet, in_dir):
		"""
		Given a packet, return the (link, emergency_link) pair to which the packet
		should be sent. The emergency link may be the same as the regular link.
		"""
		
		if packet.emergency:
			assert(in_dir is not None)
			
			# The packet is being emergency-routed, send it to its original target
			# which is the link counter-clockwise to the link it arrived
			route = self.out_links[topology.next_ccw(in_dir)]
			return (route, route)
		elif packet.destination == self.mesh_position:
			# Packet was destined to end up at this node
			return (self.exit_link, self.exit_link)
		else:
			# Find the shortest path to the destination
			shortest_path = topology.get_path(topology.zero_pad(self.mesh_position),
			                                  topology.zero_pad(packet.destination),
			                                  self.mesh_dimensions)
			
			# Do direction-order-routing
			if   shortest_path[0] > 0: direction = topology.EAST
			elif shortest_path[0] < 0: direction = topology.WEST
			elif shortest_path[1] > 0: direction = topology.NORTH
			elif shortest_path[1] < 0: direction = topology.SOUTH
			elif shortest_path[2] > 0: direction = topology.SOUTH_WEST
			elif shortest_path[2] < 0: direction = topology.NORTH_EAST
			else: assert(False)
			
			# The emergency route takes the link counter-clockwise to the intended
			# direction
			return (self.out_links[direction], self.out_links[topology.next_ccw(direction)])
