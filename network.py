#!/usr/bin/env python

"""
Network primitives such as "chips", "boards" and "tiles".
"""

from router import SpiNNakerRouter

from core import SpiNNakerTrafficGenerator

from link import DeadLink
from link import BufferLink
from link import SilistixLink
from link import SATALink

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
	
	
	def get_mesh_position(self):
		"""
		Set the size of the mesh of chips this system is in.
		"""
		return self.router.get_mesh_position()
	
	
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



class SpiNNakerTorus(object):
	"""
	Assembles a set of boards connected in a torus as in the larger, multi-board
	machines.
	
	The system contains a rectangular array of three-board board-sets. A single
	board set is shown below. Each board's nodes are represented by their number.
	(The first node in the hexagon has been replaced with a $). 
	
	1 1 1 1 2 2 2 2 $ 2 2 2
	1 1 1 1 2 2 2 2 2 2 2 1
	1 1 1 1 2 2 2 2 2 2 1 1
	1 1 1 1 2 2 2 2 2 1 1 1
	$ 1 1 1 0 0 0 0 1 1 1 1
	1 1 1 0 0 0 0 0 1 1 1 1
	1 1 0 0 0 0 0 0 1 1 1 1
	1 0 0 0 0 0 0 0 1 1 1 1
	0 0 0 0 $ 0 0 0 2 2 2 2
	0 0 0 0 0 0 0 2 2 2 2 2
	0 0 0 0 0 0 2 2 2 2 2 2
	0 0 0 0 0 2 2 2 2 2 2 2
	
	Board-sets can be wrapped into a torus if opposing edges are connected in the
	obvious way. Three boards is the minimum number of boards in such a set and
	this model only allows repetitions of this pattern (it may not be possible to
	do otherwise anyway, I don't actually know).
	
	The full SpiNNaker 106 machine would comprise of a 20x20 board-set system.
	"""
	
	def __init__( self
	            , scheduler
	            , system
	            
	            , width
	            , height
	            
	            , sata_accept_period      # SATALink
	            , sata_buffer_length      # SATALink
	            , sata_latency            # SATALink
	            
	            , silistix_send_cycles    # SilistixLink
	            , silistix_ack_cycles     # SilistixLink
	            
	            , injection_buffer_length # SpiNNaker101
	            
	            , router_period           # SpiNNakerRouter
	            , wait_before_emergency   # SpiNNakerRouter
	            , wait_before_drop        # SpiNNakerRouter
	            
	            , core_period             # SpiNNakerTrafficGenerator
	            , packet_prob             # SpiNNakerTrafficGenerator
	            , distance_std = None     # SpiNNakerTrafficGenerator
	            ):
		"""
		width is the number of three-board board-sets wide the system will be.
		
		height is the number of three-board board-sets tall the system will be.
		
		sata_accept_period see SATALink
		sata_buffer_length see SATALink
		sata_latency see SATALink
		
		silistix_send_cycles see SilistixLink
		silistix_ack_cycles see SilistixLink
		
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
		
		self.width  = width
		self.height = height
		
		# A dictionary { (x,y): SpiNNaker103, ... } of all contained boards. The
		# coordinates are relative to the bottom-leftmost board (which is not
		# wrapped around). A full board is two units wide and two units tall in this
		# coordinate system.
		self.boards = { }
		
		# The size of the mesh of chips: twelve chips per board set
		mesh_dimensions = (self.width * 12, self.height * 12)
		
		# Initially create all the boards
		for y in range(self.height):
			for x in range(self.width):
				# z is the index of the board within the set. 0 is the bottom left, 1 is
				# the top, 2 is the right
				for z in range(3):
					# Odd-rows start offset by one unit right, odd columns start offset one
					# unit up.
					board = SpiNNaker103( scheduler
					                    , system
					                    , silistix_send_cycles
					                    , silistix_ack_cycles
					                    , injection_buffer_length
					                    , router_period
					                    , wait_before_emergency
					                    , wait_before_drop
					                    , core_period
					                    , packet_prob
					                    , distance_std
					                    )
					
					# The coordinates of a board within the set of boards
					x_coord = x*3 + z
					y_coord = y*3 + (3-z)%3
					self.boards[(x_coord, y_coord)] = board
					
					# Set the board's position in terms of the whole system
					board.set_mesh_dimensions(*mesh_dimensions)
					x_mesh_coord = x_coord*4
					y_mesh_coord = y_coord*4
					board.set_mesh_position(x_mesh_coord, y_mesh_coord)
					
					# If the board is on a right/top edge, the right/top half of its chips are
					# actually on the left-hand-side/bottom of the system
					if x_coord == (self.width*3)-1:
						board.set_mesh_position_right(0, y_mesh_coord)
					if y_coord == (self.height*3)-1:
						# Plus one is due to the bottom edge of the hexagons being longer than
						# the left-edge
						board.set_mesh_position_top(x_mesh_coord+1, 0)
		
		# Now link every board with all those above and to the right
		for board_coords, board in self.boards.iteritems():
			top_board_coords = ( (board_coords[0]+1) % (self.width*3)
			                   , (board_coords[1]+2) % (self.height*3)
			                   )
			top_right_board_coords = ( (board_coords[0]+2) % (self.width*3)
			                         , (board_coords[1]+1) % (self.height*3)
			                         )
			btm_right_board_coords = ( (board_coords[0]+1) % (self.width*3)
			                         , (board_coords[1]-1) % (self.height*3)
			                         )
			
			# Create the links for these edges
			for other_coords, edge in ( (top_board_coords,       topology.EDGE_TOP)
			                          , (top_right_board_coords, topology.EDGE_TOP_RIGHT)
			                          , (btm_right_board_coords, topology.EDGE_BOTTOM_RIGHT)
			                          ):
				other_board = self.boards[other_coords]
				
				# From board to other_board
				in_link = SATALink( self.scheduler
				                  , 8 # num_channels
				                  , sata_accept_period
				                  , sata_buffer_length
				                  , sata_latency
				                  , silistix_send_cycles
				                  , silistix_ack_cycles
				                  )
				# From other_board to board
				out_link = SATALink( self.scheduler
				                   , 8 # num_channels
				                   , sata_accept_period
				                   , sata_buffer_length
				                   , sata_latency
				                   , silistix_send_cycles
				                   , silistix_ack_cycles
				                   )
				
				# Link up each of the channels on this edge in both directions
				for channel in range(8):
					in_channel  = in_link.get_channel_link(channel)
					out_channel = out_link.get_channel_link(channel)
					
					board.set_in_link(edge, channel,  in_channel)
					board.set_out_link(edge, channel, out_channel)
					
					other_board.set_out_link(topology.opposite(edge), channel, in_channel)
					other_board.set_in_link(topology.opposite(edge), channel,  out_channel)
