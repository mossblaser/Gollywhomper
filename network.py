#!/usr/bin/env python

"""
Network primitives such as "chips", "boards" and "tiles".
"""

from router import SpiNNakerRouter

from core import SpiNNakerTrafficGenerator

from link import DeadLink
from link import BufferLink
from link import SilistixLink

import topology


class SpiNNaker101(object):
	"""
	A single SpiNNaker chip, a 101 machine in SpiNNaker parlance.
	
	Contains a traffic generator and router. The links from the router are
	initially dead.
	"""
	
	def __init__( self
	            , scheduler
	            , system
	            
	            , injection_buffer_length
	            
	            , router_period          # SpiNNakerRouter
	            , wait_before_emergency  # SpiNNakerRouter
	            , wait_before_drop       # SpiNNakerRouter
	            
	            , core_period            # SpiNNakerTrafficGenerator
	            , packet_prob            # SpiNNakerTrafficGenerator
	            , distance_std = None    # SpiNNakerTrafficGenerator
	            ):
		"""
		injection_buffer_length is the number of packets that can be buffered internally
		before they're routed.
		
		router_period see SpiNNakerRouter
		wait_before_emergency see SpiNNakerRouter
		wait_before_drop see SpiNNakerRouter
		
		core_period see SpiNNakerTrafficGenerator
		packet_prob see SpiNNakerTrafficGenerator
		distance_std see SpiNNakerTrafficGenerator
		"""
		
		self.scheduler = scheduler
		self.system    = system
		
		# Links between the router and traffic generator
		injection_link = BufferLink(self.scheduler, injection_buffer_length)
		exit_link      = BufferLink(self.scheduler)
		
		# The external connections to the rest of the world
		self.in_links = [DeadLink(self.scheduler)]*6
		self.out_links = [DeadLink(self.scheduler)]*6
		
		self.traffic_generator = SpiNNakerTrafficGenerator( self.scheduler
		                                                  , self.system
		                                                  , core_period
		                                                  , packet_prob
		                                                  , injection_link
		                                                  , exit_link
		                                                  , distance_std
		                                                  )
		
		self.router = SpiNNakerRouter( self.scheduler
		                             , self.system
		                             , injection_link
		                             , exit_link
		                             , self.in_links
		                             , self.out_links
		                             , router_period
		                             , wait_before_emergency
		                             , wait_before_drop
		                             )
		
	
	
	def set_mesh_dimensions(self, w, h):
		"""
		Set the size of the mesh of chips this system is in.
		"""
		self.traffic_generator.set_mesh_dimensions(w,h)
		self.router.set_mesh_dimensions(w,h)
	
	
	def set_mesh_position(self, x, y):
		"""
		Set the size of the mesh of chips this system is in.
		"""
		self.traffic_generator.set_mesh_position(x,y)
		self.router.set_mesh_position(x,y)
	
	
	def set_in_link(self, direction, link):
		"""
		Set the given link to the link specified.
		"""
		self.in_links[direction] = link
	
	
	def set_out_link(self, direction, link):
		"""
		Set the given link to the link specified.
		"""
		self.out_links[direction] = link
	
	
	def get_in_link(self, direction):
		"""
		Get the link specified.
		"""
		return self.in_links[direction]
	
	
	def get_out_link(self, direction):
		"""
		Get the link specified.
		"""
		return self.out_links[direction]



class SpiNNaker103(object):
	"""
	Assembles a board with the same topology as the SpiNNaker 103 machine board
	with 48 chips arranged in a hexagon with SilistixLinks used for all internal
	connections.
	
	The chips are arranged in a hexagon (shown here mapped to x/y with the chip at
	0,0 marked as 0). This matrix is further dividable into halves as shown
	
	        # # # #--+-
	      # # # # #  |   Top Half
	    # # # # # #  |
	  # # # # # # #--+-
	# # # # 0 # # #--+-
	# # # # # # # |  |   Bottom Half
	# # # # # #   |  |
	# # # # #-----+--+-
	|     | |     |
	+-----+ +-----+
	|     | |     |
	 Left    Right
	 Half    Half
	
	The "edges" of the board are labelled below
	           11111111
	         00# # # #22
	       00# # # # #22  EDGE_TOP         = 0
	     00# # # # # #22  EDGE_TOP_LEFT    = 1
	   00# # # # # # #22  EDGE_BOTTOM_LEFT = 2
	  5# # # # 0 # # #3   EDGE_BOTTOM      = 3
	 55# # # # # # #33    EDGE_BOTTOM_RIGHT= 4
	 55# # # # # #33      EDGE_TOP_RIGHT   = 5
	 55# # # # #33
	  5444444443
	"""
	
	def __init__( self
	            , scheduler
	            , system
	            
	            , link_send_cycles        # SilistixLink
	            , link_ack_cycles         # SilistixLink
	            
	            , injection_buffer_length # SpiNNaker101
	            
	            , router_period           # SpiNNakerRouter
	            , wait_before_emergency   # SpiNNakerRouter
	            , wait_before_drop        # SpiNNakerRouter
	            
	            , core_period             # SpiNNakerTrafficGenerator
	            , packet_prob             # SpiNNakerTrafficGenerator
	            , distance_std = None     # SpiNNakerTrafficGenerator
	            ):
		"""
		link_send_cycles see SilistixLink
		link_ack_cycles see SilistixLink
		
		injection_buffer_length see SpiNNaker101
		
		router_period see SpiNNakerRouter
		wait_before_emergency see SpiNNakerRouter
		wait_before_drop see SpiNNakerRouter
		
		core_period see SpiNNakerTrafficGenerator
		packet_prob see SpiNNakerTrafficGenerator
		distance_std see SpiNNakerTrafficGenerator
		"""
		
		self.scheduler               = scheduler
		self.system                  = system
		
		# A dictionary { (x,y): SpiNNaker101, ... } of all contained chips. The
		# coordinates are relative to the central chip (created first in the
		# hexagon).
		self.chips = { }
		
		# Utility function to add a new chip to the chips dict.
		def add_chip(position):
			"Add a chip at the specified position"
			self.chips[position] = SpiNNaker101( self.scheduler
			                                   , self.system
			                                   , injection_buffer_length
			                                   , router_period
			                                   , wait_before_emergency
			                                   , wait_before_drop
			                                   , core_period
			                                   , packet_prob
			                                   , distance_std
			                                   )
		# Create the chips in a hexagonal pattern
		for position in topology.hexagon(4):
			add_chip(position)
		
		# Put SilistixLinks between them
		for src_pos, src_chip in self.chips.iteritems():
			# Try and link this chip to all other neighbours which are towards the
			# top/right of the chip
			for direction in (topology.NORTH, topology.NORTH_EAST, topology.EAST):
				dst_pos = topology.to_xy(
					topology.add_direction(topology.zero_pad(src_pos), direction))
				
				# If the chip exists, put links in this direction
				if dst_pos in self.chips:
					dst_chip = self.chips[dst_pos]
					
					in_link  = SilistixLink(self.scheduler, link_send_cycles, link_ack_cycles)
					out_link = SilistixLink(self.scheduler, link_send_cycles, link_ack_cycles)
					
					src_chip.set_out_link(direction, out_link)
					src_chip.set_in_link(direction, in_link)
					
					dst_chip.set_in_link(topology.opposite(direction), out_link)
					dst_chip.set_out_link(topology.opposite(direction), in_link)
	
	
	def set_mesh_dimensions(self, w, h):
		"""
		Set the size of the mesh of chips this system is in.
		"""
		for chip in self.chips.itervalues():
			chip.set_mesh_dimensions(w, h)
	
	
	def set_mesh_position_top(self, x, y):
		"""
		Set the (x,y) position of the bottom-leftmost chip in the top half of the
		array and the others in the top half as you would expect. The bottom half
		is not changed.
		"""
		for pos, chip in self.chips.iteritems():
			if pos[1] >= 1:
				chip.set_mesh_position(x + pos[0] + 3, y + pos[1] - 1)
	
	
	def set_mesh_position_bottom(self, x, y):
		"""
		Set the (x,y) position of the bottom-leftmost chip in the bottom half of the
		array and the others in the bottom half as you would expect. The top half
		is not changed.
		"""
		for pos, chip in self.chips.iteritems():
			if pos[1] <= 0:
				chip.set_mesh_position(x + pos[0] + 4, y + pos[1] + 3)
	
	
	def set_mesh_position_right(self, x, y):
		"""
		Set the (x,y) position of the bottom-leftmost chip in the right half of the
		array and the others in the right half as you would expect. The left half is
		not changed.
		"""
		for pos, chip in self.chips.iteritems():
			if pos[0] >= 0:
				chip.set_mesh_position(x + pos[0], y + pos[1] + 4 - 1)
	
	
	def set_mesh_position_left(self, x, y):
		"""
		Set the (x,y) position of the bottom-leftmost chip in the left half of the
		array and the others in the left half as you would expect. The right half is
		not changed.
		"""
		for pos, chip in self.chips.iteritems():
			if pos[0] < 0:
				chip.set_mesh_position(x + pos[0] + 4, y + pos[1] + 4 - 1)
	
	
	def set_mesh_position(self, x, y):
		"""
		Set the position of the whole board in the system with (x,y) being the
		position of the bottom-left chip.
		"""
		# Just use the left/right half utilities to move the points
		self.set_mesh_position_left(x,y)
		self.set_mesh_position_right(x+4,y)
	
	
	def set_in_link(self, edge, num, link):
		"""
		Set the link on the given edge and num.
		"""
		position, direction = topology.hexagon_edge_link(edge, num, 4)
		self.chips[position].set_in_link(direction, link)
	
	
	def set_out_link(self, edge, num, link):
		"""
		Set the link on the given edge and num.
		"""
		position, direction = topology.hexagon_edge_link(edge, num, 4)
		self.chips[position].set_out_link(direction, link)
	
	
	def get_in_link(self, edge, num):
		"""
		Get the link specified.
		"""
		position, direction = topology.hexagon_edge_link(edge, num, 4)
		return self.chips[position].get_in_link(direction)
	
	
	def get_out_link(self, edge, num):
		"""
		Get the link specified.
		"""
		position, direction = topology.hexagon_edge_link(edge, num, 4)
		return self.chips[position].get_out_link(direction)


