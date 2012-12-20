#!/usr/bin/env python

"""
Unit tests. Not comprehensive but just quick and dirty... Usage:

python tests.py
"""

import unittest

from itertools import product

from scheduler import Scheduler

from link import SilistixLink
from link import DeadLink
from link import BufferLink
from link import DelayLineLink
from link import SATALink

from system import SpiNNakerSystem

from packet import SpiNNakerP2PPacket

from router import SpiNNakerRouter

from core import SpiNNakerTrafficGenerator

from top import SpiNNaker101
from top import SpiNNaker103
from top import SpiNNakerTorus

import topology

class SchedulerTests(unittest.TestCase):
	"""
	Tests the scheduler does something sensible.
	"""
	
	def test_term_on_empty(self):
		# If nothing is scheduled, the system should terminate immediately
		s = Scheduler()
		self.assertRaises(StopIteration, s.run().next)
	
	def test_do_now(self):
		# If I schedule something now, it happens in the zeroth clock and then it
		# exits
		s = Scheduler()
		s.do_now((lambda: None))
		iterator = s.run()
		self.assertEqual(iterator.next(), 0)
		self.assertRaises(StopIteration, iterator.next)
	
	def test_do_later(self):
		# If I schedule something later, it happens after something which happens
		# now
		
		now_called   = [False]
		def for_now(): now_called[0] = True
		later_called = [False]
		def for_later(): later_called[0] = True
		much_later_called = [False]
		def for_much_later(): much_later_called[0] = True
		
		
		s = Scheduler()
		s.do_now(for_now)
		s.do_later(for_later)
		s.do_later(for_much_later, 10)
		
		iterator = s.run()
		
		self.assertTrue(    not now_called[0]
		                and not later_called[0]
		                and not much_later_called[0])
		
		self.assertEqual(iterator.next(), 0)
		self.assertTrue(        now_called[0]
		                and not later_called[0]
		                and not much_later_called[0])
		
		self.assertEqual(iterator.next(), 0)
		self.assertTrue(        now_called[0]
		                and     later_called[0]
		                and not much_later_called[0])
		
		self.assertEqual(iterator.next(), 10)
		self.assertTrue(        now_called[0]
		                and     later_called[0]
		                and     much_later_called[0])
		
		self.assertRaises(StopIteration, iterator.next)



class LinkTests(unittest.TestCase):
	"""
	Tests the link models do something reasonable.
	"""
	
	def test_silistix_link(self):
		s = Scheduler()
		sl = SilistixLink(s, 10, 5)
		
		# A simple packet container
		class Packet(object):
			def __init__(self,data,length):
				self.data   = data
				self.length = length
		
		# Initially can send
		self.assertTrue(sl.can_send())
		self.assertFalse(sl.can_receive())
		
		sl.send(Packet(123,2))
		
		# Can't send after sending something
		self.assertFalse(sl.can_send())
		self.assertFalse(sl.can_receive())
		
		it = s.run()
		
		# Can't send or recieve until send delay has elapsed
		while it.next() != 10*2 + 5*1:
			self.assertFalse(sl.can_send())
			self.assertFalse(sl.can_receive())
		
		# Can only recieve once data is stable
		self.assertFalse(sl.can_send())
		self.assertTrue(sl.can_receive())
		
		# Can peek
		self.assertEqual(sl.peek().data, 123)
		self.assertFalse(sl.can_send())
		self.assertTrue(sl.can_receive())
		self.assertEqual(sl.peek().data, 123)
		self.assertFalse(sl.can_send())
		self.assertTrue(sl.can_receive())
		
		# Recieved data is correct
		self.assertEqual(sl.receive().data, 123)
		
		# Can't recieve any more
		self.assertFalse(sl.can_send())
		self.assertFalse(sl.can_receive())
		
		# Can't send or recieve until Acknowledge arrives
		while it.next() != 10*2 + 5*2:
			self.assertFalse(sl.can_send())
			self.assertFalse(sl.can_receive())
		
		# Can send once ack is back
		self.assertTrue(sl.can_send())
		self.assertFalse(sl.can_receive())
		
		# Nothing else got scheduled...
		self.assertRaises(StopIteration, it.next)
	
	
	def test_dead_link(self):
		s = Scheduler()
		dl = DeadLink(s)
		
		# Can't do anything...
		self.assertFalse(dl.can_send())
		self.assertFalse(dl.can_receive())
		
		# Didn't schedule anything
		self.assertRaises(StopIteration, s.run().next)
	
	
	def test_buffer_link(self):
		s = Scheduler()
		bl = BufferLink(s, 2)
		
		# Can only send
		self.assertTrue(bl.can_send())
		self.assertFalse(bl.can_receive())
		
		bl.send(123)
		
		# Have something to recieve and space left
		self.assertTrue(bl.can_send())
		self.assertTrue(bl.can_receive())
		
		bl.send(456)
		
		# Have something to recieve and no space left
		self.assertFalse(bl.can_send())
		self.assertTrue(bl.can_receive())
		
		# Can peek
		self.assertEqual(bl.peek(), 123)
		self.assertFalse(bl.can_send())
		self.assertTrue(bl.can_receive())
		self.assertEqual(bl.peek(), 123)
		self.assertFalse(bl.can_send())
		self.assertTrue(bl.can_receive())
		
		# In queue order
		self.assertEqual(bl.receive(), 123)
		
		# Still have something to recieve and space left again
		self.assertTrue(bl.can_send())
		self.assertTrue(bl.can_receive())
		
		# Can peek
		self.assertEqual(bl.peek(), 456)
		self.assertTrue(bl.can_send())
		self.assertTrue(bl.can_receive())
		self.assertEqual(bl.peek(), 456)
		self.assertTrue(bl.can_send())
		self.assertTrue(bl.can_receive())
		
		# In queue order
		self.assertEqual(bl.receive(), 456)
		
		# Nothing to recieve and space in buffer
		self.assertTrue(bl.can_send())
		self.assertFalse(bl.can_receive())
		
		# Didn't schedule anything
		self.assertRaises(StopIteration, s.run().next)
	
	def test_delay_line_link(self):
		s = Scheduler()
		sys = SpiNNakerSystem(s, 1000)
		dll = DelayLineLink(s, 5)
		
		# An example packet
		p = SpiNNakerP2PPacket(sys, "Data", (0,0), 1)
		
		# Can't receive initially but can send
		self.assertFalse(dll.can_receive())
		self.assertTrue(dll.can_send())
		
		it = s.run()
		
		# Does nothing (but keeps scheduling things) if we give it nothing to do
		while it.next() < 100:
			self.assertFalse(dll.can_receive())
			self.assertTrue(dll.can_send())
		# Something happens every cycle...
		self.assertTrue(s.clock == 100)
		
		# Send a packet down the link
		dll.send(p)
		# Can't receive yet
		self.assertFalse(dll.can_receive())
		self.assertTrue(dll.can_send())
		
		# Nothing arrives in four cycles
		while it.next() <= 104:
			self.assertFalse(dll.can_receive())
			self.assertTrue(dll.can_send())
		
		# Something arrives in the fifth cycle
		arrived = False
		while it.next() <= 105:
			arrived = arrived or dll.can_receive()
			self.assertTrue(dll.can_send())
		self.assertTrue(arrived and dll.can_receive())
		
		# Can still receive even if we leave it a moment...
		while it.next() < 150:
			self.assertTrue(dll.can_receive())
			self.assertTrue(dll.can_send())
		
		# Can receive the packet happily
		self.assertEqual(dll.receive(), p)
		self.assertFalse(dll.can_receive())
		self.assertTrue(dll.can_send())
	
	
	def test_sata_link(self):
		s = Scheduler()
		sys = SpiNNakerSystem(s, 1000)
		num_channels = 2
		dll = SATALink( s
		              , num_channels  # num_channels
		              , 2  # sata_accept_period
		              , 1  # sata_buffer_length
		              , 40 # sata_latency
		              , 10 # silistix_send_cycles
		              , 5  # silistix_ack_cycles
		              )
		
		# Example packets
		packets = [SpiNNakerP2PPacket(sys, "Data %d"%n, (0,0), 1)
		           for n in range(num_channels)]
		
		channels = [dll.get_channel_link(n) for n in range(num_channels)]
		
		it = s.run()
		it_next = 0
		
		# Can only send initially
		while it.next() < it_next + 100:
			for c in channels:
				self.assertTrue(c.can_send())
				self.assertFalse(c.can_receive())
		it_next += 100
		
		
		# Can send packets down each channel individually?
		for p,c in zip(packets,channels):
			# Put the packet in the channel
			self.assertTrue(c.can_send())
			c.send(p)
			self.assertFalse(c.can_send())
			
			while it.next() < it_next + 100:
				# Check nothing happens on the other channels
				for c_ in channels:
					if c != c_:
						self.assertTrue(c_.can_send())
						self.assertFalse(c_.can_receive())
			it_next += 100
			
			# Check the packet arrived
			self.assertTrue(c.can_receive())
			self.assertEqual(c.receive(), p)
			self.assertFalse(c.can_receive())
		
		# Can send packets down each channels all at once?
		for p,c in zip(packets,channels):
			self.assertTrue(c.can_send())
			c.send(p)
			self.assertFalse(c.can_send())
		
		# Wait for them all to get there
		while it.next() < it_next + 100:
			pass
		it_next += 100
			
		# Check the packets arrived
		for p,c in zip(packets,channels):
			self.assertTrue(c.can_receive())
			self.assertEqual(c.receive(), p)
			self.assertFalse(c.can_receive())
		
		# Can a single channel block while all others don't?
		while channels[0].can_send():
			self.assertTrue(channels[0].can_send())
			channels[0].send(p)
			self.assertFalse(channels[0].can_send())
			
			# Wait for the packet to get buffered
			while it.next() < it_next + 100:
				pass
			it_next += 100
		
		# Channel is blocked
		self.assertFalse(channels[0].can_send())
		
		# Other channels are not
		for c in channels[1:]:
			self.assertTrue(c.can_send())



class SystemTests(unittest.TestCase):
	"""
	Tests the system model does something reasonable.
	"""
	
	def test_system(self):
		s = Scheduler()
		sys = SpiNNakerSystem(s, 10)
		
		it = s.run()
		
		last_clock = 0
		
		prev_phases = []
		for _ in range(8):
			# The previous cycle doesn't qualify for expiry
			if len(prev_phases) >= 1:
				self.assertNotEqual(prev_phases[-1] ^ sys.time_phase, 0b11)
			
			# The previous cycle-but-one qualifies for expiry
			if len(prev_phases) >= 2:
				self.assertEqual(prev_phases[-2] ^ sys.time_phase, 0b11)
			
			prev_phases.append(sys.time_phase)
			
			# Scheduled the phase update correctly
			self.assertEqual(it.next(), last_clock + 10)
			last_clock += 10



class PacketTests(unittest.TestCase):
	"""
	Test the packet container.
	"""
	
	def test_expire(self):
		# Tests that packets expire
		
		s = Scheduler()
		# The time-step increments once per 10 ticks
		sys = SpiNNakerSystem(s, 10)
		
		# Make a packet
		p = SpiNNakerP2PPacket(sys, "Data", (0,0), 1)
		
		it = s.run()
		
		# Not expired initially
		self.assertFalse(p.has_expired())
		
		# After one time step, its still not expired
		while it.next() < 10: pass
		self.assertFalse(p.has_expired())
		
		# After two time step, its has expired!
		while it.next() < 10: pass
		self.assertTrue(p.has_expired())


class TopologyTests(unittest.TestCase):
	"""
	Tests the topology utility functions
	"""
	
	def test_next(self):
		cw  = topology.next_cw
		ccw = topology.next_ccw
		
		# Clockwise
		self.assertEqual(cw(topology.EAST),       topology.SOUTH)
		self.assertEqual(cw(topology.NORTH_EAST), topology.EAST)
		self.assertEqual(cw(topology.NORTH),      topology.NORTH_EAST)
		self.assertEqual(cw(topology.WEST),       topology.NORTH)
		self.assertEqual(cw(topology.SOUTH_WEST), topology.WEST)
		self.assertEqual(cw(topology.SOUTH),      topology.SOUTH_WEST)
		
		# Counter-Clockwise
		self.assertEqual(ccw(topology.EAST),       topology.NORTH_EAST)
		self.assertEqual(ccw(topology.NORTH_EAST), topology.NORTH)
		self.assertEqual(ccw(topology.NORTH),      topology.WEST)
		self.assertEqual(ccw(topology.WEST),       topology.SOUTH_WEST)
		self.assertEqual(ccw(topology.SOUTH_WEST), topology.SOUTH)
		self.assertEqual(ccw(topology.SOUTH),      topology.EAST)
	
	def test_opposite(self):
		opp = topology.opposite
		
		self.assertEqual(opp(topology.EAST),       topology.WEST)
		self.assertEqual(opp(topology.NORTH_EAST), topology.SOUTH_WEST)
		self.assertEqual(opp(topology.NORTH),      topology.SOUTH)
		self.assertEqual(opp(topology.WEST),       topology.EAST)
		self.assertEqual(opp(topology.SOUTH_WEST), topology.NORTH_EAST)
		self.assertEqual(opp(topology.SOUTH),      topology.NORTH)
	
	def test_direction(self):
		ad = topology.add_direction
		
		self.assertEqual(ad((11,11,11), topology.EAST),       (12,11,11))
		self.assertEqual(ad((11,11,11), topology.NORTH_EAST), (11,11,10))
		self.assertEqual(ad((11,11,11), topology.NORTH),      (11,12,11))
		self.assertEqual(ad((11,11,11), topology.WEST),       (10,11,11))
		self.assertEqual(ad((11,11,11), topology.SOUTH_WEST), (11,11,12))
		self.assertEqual(ad((11,11,11), topology.SOUTH),      (11,10,11))
	
	
	def test_manhattan(self):
		self.assertEqual(topology.manhattan([0]),      0)
		self.assertEqual(topology.manhattan([1]),      1)
		self.assertEqual(topology.manhattan([-1]),     1)
		self.assertEqual(topology.manhattan([-1, 0]),  1)
		self.assertEqual(topology.manhattan([-1, -1]), 2)
		self.assertEqual(topology.manhattan([-1,  1]), 2)
	
	
	def test_median_element(self):
		self.assertEqual(topology.median_element([0]), 0)
		self.assertEqual(topology.median_element([0,1,2]), 1)
		self.assertEqual(topology.median_element([2,1,0]), 1)
		self.assertEqual(topology.median_element([1,2,0]), 1)
		self.assertEqual(topology.median_element([2,0,1]), 1)
		self.assertEqual(topology.median_element([2,2,2]), 2)
	
	
	def test_to_shortest_path(self):
		self.assertEqual(topology.to_shortest_path((0,0,0)), (0,0,0))
		self.assertEqual(topology.to_shortest_path((1,1,1)), (0,0,0))
		self.assertEqual(topology.to_shortest_path((0,1,2)), (-1,0,1))
		self.assertEqual(topology.to_shortest_path((-2,0,2)), (-2,0,2))
	
	
	def test_to_xy(self):
		self.assertEqual(topology.to_xy((0,0,0)), (0,0))
		self.assertEqual(topology.to_xy((1,1,1)), (0,0))
		self.assertEqual(topology.to_xy((0,1,2)), (-2,-1))
		self.assertEqual(topology.to_xy((-2,0,2)), (-4,-2))
	
	
	def test_get_path(self):
		gp = topology.get_path
		# Simple case (just a delta and to_shortest_path
		self.assertEqual(gp((0,0,0), (0,0,0)),   (0,0,0))
		self.assertEqual(gp((0,0,0), (1,1,0)),   (0,0,-1))
		self.assertEqual(gp((5,5,0), (10,10,0)), (0,0,-5))
		
		# In a repeating 12-12 mesh.
		# Simple cases: just go straight there
		self.assertEqual(gp((0,0,0), (0,0,0),   (12,12)), (0,0,0))
		self.assertEqual(gp((0,0,0), (1,1,0),   (12,12)), (0,0,-1))
		self.assertEqual(gp((5,5,0), (10,10,0), (12,12)), (0,0,-5))
		
		# Have to wrap around the edges for shortest path
		self.assertEqual(gp((0,0,0), (11,0,0),  (12,12)), (-1,0,0))
		self.assertEqual(gp((0,0,0), (0,11,0),  (12,12)), (0,-1,0))
		self.assertEqual(gp((0,0,0), (11,11,0), (12,12)), (0,0,1))
	
	
	def test_hexagon(self):
		it = topology.hexagon(2)
		
		# Inner layer
		self.assertEqual(it.next(), ( 0, 0))
		self.assertEqual(it.next(), (-1, 0))
		self.assertEqual(it.next(), ( 0, 1))
		
		# Outer layer
		self.assertEqual(it.next(), ( 1, 1))
		self.assertEqual(it.next(), ( 1, 0))
		self.assertEqual(it.next(), ( 0,-1))
		self.assertEqual(it.next(), (-1,-1))
		self.assertEqual(it.next(), (-2,-1))
		self.assertEqual(it.next(), (-2, 0))
		self.assertEqual(it.next(), (-1, 1))
		self.assertEqual(it.next(), ( 0, 2))
		self.assertEqual(it.next(), ( 1, 2))
		
		# Stop now
		self.assertRaises(StopIteration, it.next)
	
	def test_hexagon_edge_link(self):
		# Get the set of edge nodes for a 4-layer hexagon
		all_nodes   = set(topology.hexagon(4))
		inner_nodes = set(topology.hexagon(3))
		outer_nodes = all_nodes - inner_nodes
		
		directions = [
			topology.EAST,
			topology.NORTH_EAST,
			topology.NORTH,
			topology.WEST,
			topology.SOUTH_WEST,
			topology.SOUTH
		]
		
		edges = [
			topology.EDGE_TOP_LEFT,
			topology.EDGE_TOP,
			topology.EDGE_TOP_RIGHT,
			topology.EDGE_BOTTOM_RIGHT,
			topology.EDGE_BOTTOM,
		  topology.EDGE_BOTTOM_LEFT,
		]
		
		# Get the set of outward-facing links as (node_xy,direction) pairs
		outward_facing_links = []
		for node in all_nodes:
			for direction in directions:
				# Get the node that this link would connect to
				facing_node = topology.to_xy(
					topology.add_direction(topology.zero_pad(node), direction))
				# If that node isn't part of our set, it is an edge link
				if facing_node not in all_nodes:
					outward_facing_links.append((node, direction))
		
		# Get the set of outward facing links according to the function under test
		all_links = []
		for edge in edges:
			for num in range(8):
				all_links.append(topology.hexagon_edge_link(edge, num, 4))
		
		# No duplicates
		self.assertEqual(len(all_links), len(set(all_links)))
		
		# The algorithm gets every outward facing edge
		self.assertEqual(set(all_links), set(outward_facing_links))
		



class RouterTests(unittest.TestCase):
	"""
	Tests the router
	"""
	
	TIME_PHASE_PERIOD     = 200
	ROUTER_PERIOD         = 10
	WAIT_BEFORE_EMERGENCY = 3
	WAIT_BEFORE_DROP      = 6
	
	# We're right in the middle
	MESH_DIMENSIONS       = (3,3)
	MESH_POSITION         = (1,1)
	
	def setUp(self):
		# Before each test build a new scheduler, system and router
		self.scheduler = Scheduler()
		self.system    = SpiNNakerSystem(self.scheduler, RouterTests.TIME_PHASE_PERIOD)
		
		self.injection_link = BufferLink(self.scheduler,1)
		self.exit_link      = BufferLink(self.scheduler,1)
		self.in_links       = [BufferLink(self.scheduler,1) for _ in range(6)]
		self.out_links      = [BufferLink(self.scheduler,1) for _ in range(6)]
		
		# All links
		self.links = ( [self.injection_link, self.exit_link]
		             + self.in_links
		             + self.out_links)
		
		self.router = SpiNNakerRouter( self.scheduler
		                             , self.system
		                             , self.injection_link
		                             , self.exit_link
		                             , self.in_links
		                             , self.out_links
		                             , RouterTests.ROUTER_PERIOD
		                             , RouterTests.WAIT_BEFORE_EMERGENCY
		                             , RouterTests.WAIT_BEFORE_DROP
		                             )
		self.router.set_mesh_dimensions(*RouterTests.MESH_DIMENSIONS)
		self.router.set_mesh_position(*RouterTests.MESH_POSITION)
	
	
	def test_nothing(self):
		# Test that the router does nothing if no packets are given...
		
		it = self.scheduler.run()
		while it.next() < 1000:
			pass
		
		# Nothing was sent/received
		for link in self.links:
			self.assertTrue(link.can_send())
			self.assertFalse(link.can_receive())
		
		# The router remained idle...
		self.assertEqual(self.router.counters["timestamp_packet_timeout"], 0)
		self.assertEqual(self.router.counters["router_packet_timeout"], 0)
		self.assertEqual(self.router.counters["packets_routed"], 0)
		self.assertEqual(self.router.counters["packet_emergency_routed"], 0)
		self.assertEqual(self.router.counters["router_blocked_cycles"], 0)
		
		# Some cycles occurred (i.e. it didn't stop after one)
		self.assertTrue(self.router.counters["router_cycles"] > 10)
		
		# Every cycle was idle
		self.assertEqual(self.router.counters["router_idle_cycles"],
		                 self.router.counters["router_cycles"])
	
	
	def test_loopback(self):
		# Test that the router can forward packets to itself
		
		# A packet to ourselves
		packet = SpiNNakerP2PPacket( self.system
		                           , "Example Data"
		                           , RouterTests.MESH_POSITION
		                           , 32)
		
		self.assertTrue(self.injection_link.can_send())
		self.injection_link.send(packet)
		
		# Run until the packet arrives
		it = self.scheduler.run()
		while it.next() < 1000 and not self.exit_link.can_receive():
			pass
		
		# We got our packet back
		self.assertTrue(self.exit_link.can_receive())
		rec_packet = self.exit_link.receive()
		self.assertEqual(packet, rec_packet)
		
		# Nothing else was sent/received
		for link in self.links:
			self.assertTrue(link.can_send())
			self.assertFalse(link.can_receive())
		
		# The router sent one packet...
		self.assertEqual(self.router.counters["timestamp_packet_timeout"], 0)
		self.assertEqual(self.router.counters["router_packet_timeout"], 0)
		self.assertEqual(self.router.counters["packets_routed"], 1)
		self.assertEqual(self.router.counters["packet_emergency_routed"], 0)
		self.assertEqual(self.router.counters["router_blocked_cycles"], 0)
		self.assertEqual(self.router.counters["router_idle_cycles"], 0)
		
		# This all happened in one cycle
		self.assertEqual(self.router.counters["router_cycles"], 1)
		
		# The packet took one hop
		self.assertEqual(packet.distance, 1)
		
		# Wait counter reset
		self.assertEqual(packet.wait, 0)
		
		# Not emergency routed
		self.assertFalse(packet.emergency)
	
	
	def test_normal_route(self):
		# Test that the router can forward packets to another router
		
		directions = [
			((2,1), topology.EAST),
			((0,1), topology.WEST),
			((1,2), topology.NORTH),
			((1,0), topology.SOUTH),
			((2,2), topology.NORTH_EAST),
			((0,0), topology.SOUTH_WEST),
		]
		
		for router_pos, direction in directions:
			# Reset everything...
			self.setUp()
			
			# A packet to ourselves
			packet = SpiNNakerP2PPacket( self.system
			                           , "Example Data"
			                           , router_pos
			                           , 32)
			
			# Send packet via an arbitrary input (east)
			self.assertTrue(self.in_links[0].can_send())
			self.in_links[0].send(packet)
			
			# Run until the packet arrives
			it = self.scheduler.run()
			while it.next() < 1000 and not self.out_links[direction].can_receive():
				pass
			
			# We got our packet back
			self.assertTrue(self.out_links[direction].can_receive())
			rec_packet = self.out_links[direction].receive()
			self.assertEqual(packet, rec_packet)
			
			# Nothing else was sent/received
			for link in self.links:
				self.assertTrue(link.can_send())
				self.assertFalse(link.can_receive())
			
			# The router sent one packet...
			self.assertEqual(self.router.counters["timestamp_packet_timeout"], 0)
			self.assertEqual(self.router.counters["router_packet_timeout"], 0)
			self.assertEqual(self.router.counters["packets_routed"], 1)
			self.assertEqual(self.router.counters["packet_emergency_routed"], 0)
			self.assertEqual(self.router.counters["router_blocked_cycles"], 0)
			self.assertEqual(self.router.counters["router_idle_cycles"], 0)
			
			# This all happened in one cycle
			self.assertEqual(self.router.counters["router_cycles"], 1)
			
			# The packet took one hop
			self.assertEqual(packet.distance, 1)
			
			# Wait counter reset
			self.assertEqual(packet.wait, 0)
			
			# Not emergency routed
			self.assertFalse(packet.emergency)
	
	
	def test_emergency_on_block(self):
		# Test that the router uses emergency mode when the target link is blocked
		
		directions = [
			((2,1), topology.EAST,      topology.NORTH_EAST),
			((0,1), topology.WEST,      topology.SOUTH_WEST),
			((1,2), topology.NORTH,     topology.WEST),
			((1,0), topology.SOUTH,     topology.EAST),
			((2,2), topology.NORTH_EAST,topology.NORTH),
			((0,0), topology.SOUTH_WEST,topology.SOUTH),
		]
		
		for router_pos, direction, emergency in directions:
			# Reset everything...
			self.setUp()
			
			# A dud packet
			dud = SpiNNakerP2PPacket( self.system , "Dud" , None , 1)
			
			# A packet to ourselves
			packet = SpiNNakerP2PPacket( self.system
			                           , "Example Data"
			                           , router_pos
			                           , 32)
			
			# Send packet via an arbitrary input (east)
			self.assertTrue(self.in_links[0].can_send())
			self.in_links[0].send(packet)
			
			# Block the target port with a dud packet
			self.assertTrue(self.out_links[direction].can_send())
			self.out_links[direction].send(dud)
			
			# Run until the packet arrives
			it = self.scheduler.run()
			while it.next() < 1000 and not self.out_links[emergency].can_receive():
				pass
			
			# We got our packet back
			self.assertTrue(self.out_links[emergency].can_receive())
			rec_packet = self.out_links[emergency].receive()
			self.assertEqual(packet, rec_packet)
			
			# Remove the blockage and make sure it wasn't changed...
			self.assertTrue(self.out_links[direction].can_receive())
			rec_dud = self.out_links[direction].receive()
			self.assertEqual(dud, rec_dud)
			
			# Nothing else was sent/received
			for link in self.links:
				self.assertTrue(link.can_send())
				self.assertFalse(link.can_receive())
			
			# The router sent one packet...
			self.assertEqual(self.router.counters["timestamp_packet_timeout"], 0)
			self.assertEqual(self.router.counters["router_packet_timeout"], 0)
			self.assertEqual(self.router.counters["packets_routed"], 0)
			self.assertEqual(self.router.counters["packet_emergency_routed"], 1)
			self.assertEqual(self.router.counters["router_idle_cycles"], 0)
			
			# We waited only until we could emergency route
			self.assertEqual(self.router.counters["router_blocked_cycles"],
			                 RouterTests.WAIT_BEFORE_EMERGENCY)
			
			# We executed until we waited long enough then sent the packet
			self.assertEqual(self.router.counters["router_cycles"],
			                 RouterTests.WAIT_BEFORE_EMERGENCY + 1)
			
			# The packet took one hop
			self.assertEqual(packet.distance, 1)
			
			# Wait counter reset
			self.assertEqual(packet.wait, 0)
			
			# Emergency routed
			self.assertTrue(packet.emergency)
	
	
	def test_emergency_forward(self):
		# Test that the router can forward packets received in emergency mode
		
		directions = [
			(topology.EAST,      topology.NORTH_EAST),
			(topology.WEST,      topology.SOUTH_WEST),
			(topology.NORTH,     topology.WEST),
			(topology.NORTH_EAST,topology.NORTH),
			(topology.SOUTH_WEST,topology.SOUTH),
		]
		
		for in_link, out_link in directions:
			# Reset everything...
			self.setUp()
			
			# A packet to ourselves
			packet = SpiNNakerP2PPacket( self.system
			                           , "Example Data"
			                           , (0,0) # Doesn't/Shouldn't matter
			                           , 32)
			
			# The packet is in emergency mode
			packet.emergency = True
			
			# Send packet via an arbitrary input (east)
			self.assertTrue(self.in_links[in_link].can_send())
			self.in_links[in_link].send(packet)
			
			# Run until the packet arrives
			it = self.scheduler.run()
			while it.next() < 1000 and not self.out_links[out_link].can_receive():
				pass
			
			# We got our packet back
			self.assertTrue(self.out_links[out_link].can_receive())
			rec_packet = self.out_links[out_link].receive()
			self.assertEqual(packet, rec_packet)
			
			# Nothing else was sent/received
			for link in self.links:
				self.assertTrue(link.can_send())
				self.assertFalse(link.can_receive())
			
			# The router sent one packet...
			self.assertEqual(self.router.counters["timestamp_packet_timeout"], 0)
			self.assertEqual(self.router.counters["router_packet_timeout"], 0)
			self.assertEqual(self.router.counters["packets_routed"], 1)
			self.assertEqual(self.router.counters["packet_emergency_routed"], 0)
			self.assertEqual(self.router.counters["router_idle_cycles"], 0)
			self.assertEqual(self.router.counters["router_blocked_cycles"], 0)
			
			# Routing took one cycle
			self.assertEqual(self.router.counters["router_cycles"], 1)
			
			# The packet took one hop
			self.assertEqual(packet.distance, 1)
			
			# Wait counter reset
			self.assertEqual(packet.wait, 0)
			
			# The packet is no-longer in emergency mode
			self.assertFalse(packet.emergency)
	
	
	def test_drop_on_block(self):
		# Test that the router drops packets which block
		
		directions = [
			((2,1), topology.EAST,      topology.NORTH_EAST),
			((0,1), topology.WEST,      topology.SOUTH_WEST),
			((1,2), topology.NORTH,     topology.WEST),
			((1,0), topology.SOUTH,     topology.EAST),
			((2,2), topology.NORTH_EAST,topology.NORTH),
			((0,0), topology.SOUTH_WEST,topology.SOUTH),
		]
		
		for router_pos, direction, emergency in directions:
			# Reset everything...
			self.setUp()
			
			# A dud packet
			dud = SpiNNakerP2PPacket( self.system , "Dud" , None , 1)
			
			# A packet to ourselves
			packet = SpiNNakerP2PPacket( self.system
			                           , "Example Data"
			                           , router_pos
			                           , 32)
			
			# Send packet via an arbitrary input (east)
			self.assertTrue(self.in_links[0].can_send())
			self.in_links[0].send(packet)
			
			# Block the target port with a dud packet
			self.assertTrue(self.out_links[direction].can_send())
			self.out_links[direction].send(dud)
			
			# Block the emergency port with a dud packet
			self.assertTrue(self.out_links[emergency].can_send())
			self.out_links[emergency].send(dud)
			
			# Run until the packet is dropped (the input becomes free again)
			it = self.scheduler.run()
			while it.next() < 1000 and self.in_links[0].can_receive():
				pass
			
			# Remove the blockages and make sure they weren't changed...
			self.assertTrue(self.out_links[direction].can_receive())
			rec_dud = self.out_links[direction].receive()
			self.assertEqual(dud, rec_dud)
			
			self.assertTrue(self.out_links[emergency].can_receive())
			rec_dud = self.out_links[emergency].receive()
			self.assertEqual(dud, rec_dud)
			
			# Nothing else was sent/received
			for link in self.links:
				self.assertTrue(link.can_send())
				self.assertFalse(link.can_receive())
			
			# The router dropped one packet...
			self.assertEqual(self.router.counters["timestamp_packet_timeout"], 0)
			self.assertEqual(self.router.counters["router_packet_timeout"], 1)
			self.assertEqual(self.router.counters["packets_routed"], 0)
			self.assertEqual(self.router.counters["packet_emergency_routed"], 0)
			
			# We blocked until the wait threshold was exhausted
			self.assertEqual(self.router.counters["router_blocked_cycles"],
			                 RouterTests.WAIT_BEFORE_DROP + 1)
			
			# One idle cycle where we actually drop the packet
			self.assertEqual(self.router.counters["router_idle_cycles"], 1)
			
			# We blocked until the wait threshold was exhausted plus one idle cycle
			# where we dropped the packet
			self.assertEqual(self.router.counters["router_cycles"],
			                 RouterTests.WAIT_BEFORE_DROP + 1 + 1)
			
			# The packet didn't hop
			self.assertEqual(packet.distance, 0)
			
			# The packet had to wait until the timeout expired
			self.assertEqual(packet.wait, RouterTests.WAIT_BEFORE_DROP + 1)
			
			# Not emergency routed
			self.assertFalse(packet.emergency)



class SpiNNakerTrafficGeneratorTests(unittest.TestCase):
	"""
	Tests the router
	"""
	
	def test_uniform(self):
		# Test that packets are generated appropriately when distributing with a
		# uniform distribution.
		
		scheduler = Scheduler()
		system = SpiNNakerSystem(scheduler, 10)
		
		# Share the same link for sending and receiving, that way the module cleans
		# up after itself!
		link = BufferLink(scheduler)
		
		# Uniform generator node
		tg = SpiNNakerTrafficGenerator( scheduler
		                              , system
		                              , 1
		                              , 0.1
		                              , link
		                              , link
		                              )
		tg.set_mesh_dimensions(100,100)
		tg.set_mesh_position(50,50)
		
		it = scheduler.run()
		
		# Perform 1000 cycles
		while it.next() < 2000 and tg.counters["generator_cycles"] < 1000:
			# We may have a packet
			if link.can_receive():
				# Check the packet is targeted somewhere in the mesh
				packet = link.receive()
				self.assertTrue(all(0 <= dimension < 100 for dimension in packet.destination))
		
		# Should have done 1000 cycles
		self.assertEqual(tg.counters["generator_cycles"], 1000)
		
		# We should have sent some number of packets that isn't all the time and not
		# never (well, in theory we might not but hey, if this is going wrong you've
		# got a bad day on your hands).
		self.assertTrue(10 < tg.counters["generator_injected_packets"] < 1000)
		
		# None should be dropped
		self.assertEqual(tg.counters["generator_dropped_packets"], 0)
	
	
	def test_normal(self):
		# Test that packets are generated appropriately when distributing with a
		# normal distribution.
		
		scheduler = Scheduler()
		system = SpiNNakerSystem(scheduler, 10)
		
		# Share the same link for sending and receiving, that way the module cleans
		# up after itself!
		link = BufferLink(scheduler)
		
		# Uniform generator node
		tg = SpiNNakerTrafficGenerator( scheduler
		                              , system
		                              , 1
		                              , 0.1
		                              , link
		                              , link
		                              , 10
		                              )
		tg.set_mesh_dimensions(100,100)
		tg.set_mesh_position(50,50)
		
		it = scheduler.run()
		
		# Perform 1000 cycles
		while it.next() < 2000 and tg.counters["generator_cycles"] < 1000:
			# We may have a packet
			if link.can_receive():
				# Check the packet is targeted somewhere in the mesh
				packet = link.receive()
				self.assertTrue(all(0 <= dimension < 100 for dimension in packet.destination))
		
		# XXX: Should probably check that distribution is appropriate too but meh...
		
		# Should have done 1000 cycles
		self.assertEqual(tg.counters["generator_cycles"], 1000)
		
		# We should have sent some number of packets that isn't all the time and not
		# never (well, in theory we might not but hey, if this is going wrong you've
		# got a bad day on your hands).
		self.assertTrue(10 < tg.counters["generator_injected_packets"] < 1000)
		
		# None should be dropped
		self.assertEqual(tg.counters["generator_dropped_packets"], 0)
	
	
	def test_block(self):
		# Test that packets are not generated when the link is blocked.
		
		scheduler = Scheduler()
		system = SpiNNakerSystem(scheduler, 10)
		
		link = DeadLink(scheduler)
		
		# Uniform generator node
		tg = SpiNNakerTrafficGenerator( scheduler
		                              , system
		                              , 1
		                              , 0.1
		                              , link
		                              , link
		                              )
		tg.set_mesh_dimensions(100,100)
		tg.set_mesh_position(50,50)
		
		it = scheduler.run()
		
		# Perform 1000 cycles
		while it.next() < 2000 and tg.counters["generator_cycles"] < 1000:
			pass
		
		# Should have done 1000 cycles
		self.assertEqual(tg.counters["generator_cycles"], 1000)
		
		# We should have tried to send some number of packets that isn't all the
		# time and not never (well, in theory we might not but hey, if this is going
		# wrong you've got a bad day on your hands).
		self.assertTrue(10 < tg.counters["generator_dropped_packets"] < 1000)
		
		# None should have gone out
		self.assertEqual(tg.counters["generator_injected_packets"], 0)
	
	
	
	
	def test_receive(self):
		# Test that packets are received by the unit
		
		scheduler = Scheduler()
		system = SpiNNakerSystem(scheduler, 10)
		
		# Share the same link for sending and receiving, that way the module cleans
		# up after itself!
		link = BufferLink(scheduler)
		packet = SpiNNakerP2PPacket(system, None, (0,0), 1)
		
		# Uniform generator node
		tg = SpiNNakerTrafficGenerator( scheduler
		                              , system
		                              , 1
		                              , 0
		                              , link
		                              , link
		                              , 10
		                              )
		tg.set_mesh_dimensions(100,100)
		tg.set_mesh_position(50,50)
		
		it = scheduler.run()
		
		# Perform 10 cycles, injecting some packets each time
		while it.next() < 20 and tg.counters["generator_cycles"] < 10:
			self.assertTrue(link.can_send())
			link.send(packet)
		
		# Should have done 10 cycles
		self.assertEqual(tg.counters["generator_cycles"], 10)
		
		# We should have sent no packets
		self.assertEqual(tg.counters["generator_injected_packets"], 0)
		
		# None should be dropped
		self.assertEqual(tg.counters["generator_dropped_packets"], 0)
		
		# Should have received 10 packets
		self.assertEqual(tg.counters["generator_packets_received"], 10)




class SpiNNaker101Tests(unittest.TestCase):
	"""
	Tests a chip in a very vague way...
	"""
	
	def setUp(self):
		# Test that packets are generated appropriately when distributing with a
		# uniform distribution.
		
		self.scheduler = Scheduler()
		self.system = SpiNNakerSystem(self.scheduler, 50000000)
		
		self.chip = SpiNNaker101( self.scheduler
		                        , self.system
		                        , 4 # injection_buffer_length
		                        , 10 # router_period
		                        , 300000000
		                        , 600000000
		                        , 1 # core_period
		                        , 1.0
		                        , None
		                        )
	
	
	def test_loopback(self):
		it = self.scheduler.run()
		
		# Perform 1000 cycles
		while it.next() < 4001:
			pass
		
		# Should have allowed all but 4 packets which are still in the queue
		self.assertEqual(
			self.chip.traffic_generator.counters["generator_injected_packets"] -
			self.chip.traffic_generator.counters["generator_packets_received"],
			4)
		
		# Should have routed one packet per ten cycles...
		self.assertEqual(self.chip.router.counters["packets_routed"], 400)
	
	
	def test_external(self):
		# Put the chip in a large mesh so stuff ends up there
		self.chip.set_mesh_dimensions(1000,1000)
		
		it = self.scheduler.run()
		
		# Perform 1000 cycles
		while it.next() < 4001:
			pass
		
		# Should have allowed very few packets through
		self.assertTrue(
			self.chip.traffic_generator.counters["generator_injected_packets"] < 10)
		
		# The router should be very frustrated
		self.assertTrue(self.chip.router.counters["router_blocked_cycles"] > 300)


class SpiNNaker103Tests(unittest.TestCase):
	"""
	Tests a board in a very vague way...
	"""
	
	def setUp(self):
		# Test that packets are generated appropriately when distributing with a
		# uniform distribution.
		
		self.scheduler = Scheduler()
		self.system = SpiNNakerSystem(self.scheduler, 50000000)
		
		self.board = SpiNNaker103( self.scheduler
		                         , self.system
		                         , 7 # link_send_cycles
		                         , 7 # link_ack_cycles
		                         , 4 # injection_buffer_length
		                         , 10 # router_period
		                         , 300000000
		                         , 600000000
		                         , 1 # core_period
		                         , 1.0
		                         , None
		                         )
		# Set the mesh position so that the elements have the same coordinates as
		# their internal offset.
		self.board.set_mesh_position(-4,-3)
	
	
	def test_chips(self):
		# A board should have chips in the correct locations and no repeats
		self.assertEqual(len(self.board.chips), 48)
		self.assertEqual(set(self.board.chips.iterkeys()),
		                 set(topology.hexagon(4)))
		
		# For all inputs & outputs, if there is a chip in that direction it must be
		# connected via a SilistixLink and if not it should be attached to a
		# DeadLink.
		for src_pos, src_chip in self.board.chips.iteritems():
			for direction in ( topology.EAST
			                 , topology.NORTH_EAST
			                 , topology.NORTH
			                 , topology.WEST
			                 , topology.SOUTH_WEST
			                 , topology.SOUTH
			                 ):
				in_link  = src_chip.get_in_link(direction)
				out_link = src_chip.get_out_link(direction)
				
				dst_pos = topology.to_xy(topology.add_direction(topology.zero_pad(src_pos),
				                                                direction))
				if dst_pos in self.board.chips:
					# There is a chip opposite this connection
					dst_chip = self.board.chips[dst_pos]
					direction = topology.opposite(direction)
					
					# Check that they have the same link (connected to opposite ports)
					self.assertEqual(out_link, dst_chip.get_in_link(direction))
					self.assertEqual(in_link,  dst_chip.get_out_link(direction))
					
					# And that they're SilistixLinks
					self.assertEqual(type(in_link), SilistixLink)
					self.assertEqual(type(out_link), SilistixLink)
				else:
					# No adjacent chip so should be DeadLinks
					self.assertEqual(type(in_link), DeadLink)
					self.assertEqual(type(out_link), DeadLink)
	
	
	def test_set_mesh_position(self):
		# Test the initial positions are as expected
		for pos, chip in self.board.chips.iteritems():
			self.assertEqual(pos, chip.router.mesh_position)
	
	
	def test_left_right(self):
		# Test the left and right cuts don't overlap and that they're correct
		
		# Move all the left side out of the way
		self.board.set_mesh_position_left(100-4,100-3)
		for pos, chip in self.board.chips.iteritems():
			if pos[0] < 0:
				# If on the left, should have been moved
				self.assertEqual(chip.router.mesh_position, (pos[0]+100, pos[1]+100))
			else:
				# If on the right, should have stayed
				self.assertEqual(chip.router.mesh_position, pos)
		
		# Move the right side to meet it
		self.board.set_mesh_position_right(100,100-3)
		for pos, chip in self.board.chips.iteritems():
			# All the chips should now have moved
			self.assertEqual(chip.router.mesh_position, (pos[0]+100, pos[1]+100))
	
	
	def test_top_bottom(self):
		# Test the top and bottom cuts don't overlap and that they're correct
		
		# Move all the bottom side out of the way
		self.board.set_mesh_position_bottom(100-4,100-3)
		for pos, chip in self.board.chips.iteritems():
			if pos[1] <= 0:
				# If on the bottom, should have been moved
				self.assertEqual(chip.router.mesh_position, (pos[0]+100, pos[1]+100))
			else:
				# If on the top, should have stayed
				self.assertEqual(chip.router.mesh_position, pos)
		
		# Move the top side to meet it
		self.board.set_mesh_position_top(100-3,100+1)
		for pos, chip in self.board.chips.iteritems():
			# All the chips should now have moved
			self.assertEqual(chip.router.mesh_position, (pos[0]+100, pos[1]+100))
	
	
	def test_get_set_outer_links(self):
		edges = [
			topology.EDGE_TOP_LEFT,
			topology.EDGE_TOP,
			topology.EDGE_TOP_RIGHT,
			topology.EDGE_BOTTOM_RIGHT,
			topology.EDGE_BOTTOM,
		  topology.EDGE_BOTTOM_LEFT,
		]
		
		test_link = DeadLink(self.scheduler)
		
		for edge in edges:
			for num in range(8):
				# Make sure all external links are dead
				self.assertEqual(type(self.board.get_in_link(edge,num)),  DeadLink)
				self.assertEqual(type(self.board.get_out_link(edge,num)), DeadLink)
				
				# Make sure nobody else over-wrote the node and overwrite the node
				self.assertNotEqual(self.board.get_in_link(edge,num), test_link)
				self.board.set_in_link(edge,num,test_link)
				self.assertEqual(self.board.get_in_link(edge,num), test_link)
				
				# And for out links...
				self.assertNotEqual(self.board.get_out_link(edge,num), test_link)
				self.board.set_out_link(edge,num,test_link)
				self.assertEqual(self.board.get_out_link(edge,num), test_link)



class SpiNNakerTorusTests(unittest.TestCase):
	"""
	Tests a torus of boards in a really vague way...
	"""
	
	TORUS_SIZES = [(1,1), (2,2), (1,2), (2,1), (3,3), (1,3), (3,1)]
	
	def setUp(self):
		# Test that packets are generated appropriately when distributing with a
		# uniform distribution.
		
		self.scheduler = Scheduler()
		self.system = SpiNNakerSystem(self.scheduler, 50000000)
	
	def generate_torus(self, width, height):
		# Just instantiating the torus tests that every edge has an opposing edge
		# (as links are added and this would crash otherwise (or rather did when I
		# got it wrong)).
		self.torus = SpiNNakerTorus( self.scheduler
		                           , self.system
		                           , width # width
		                           , height # height
		                           , True # use_sata_links
		                           , 1  # sata_accept_period
		                           , 4  # sata_buffer_length
		                           , 40 # sata_latency
		                           , 7 # silistix_send_cycles
		                           , 7 # silistix_ack_cycles
		                           , 4 # injection_buffer_length
		                           , 10 # router_period
		                           , 300000000 # wait_before_emergency
		                           , 600000000 # wait_before_drop
		                           , 1    # core_period
		                           , 0.01 # packet_prob
		                           , None # distance_std
		                           )
	
	
	def test_chip_positions(self):
		# Try with several sizes
		for torus_size in SpiNNakerTorusTests.TORUS_SIZES:
			self.generate_torus(*torus_size)
			
			# Check that there is exactly one chip in every x/y position
			positions = []
			for board in self.torus.boards.itervalues():
				for chip in board.chips.itervalues():
					positions.append(chip.get_mesh_position())
			
			# Check there are no duplicates
			self.assertEqual(len(positions), len(set(positions)))
			
			# Check that every chip exists that should
			self.assertEqual(set(positions), set(product( range(self.torus.width*12)
			                                            , range(self.torus.height*12)
			                                            )))
	
	
	def test_connections(self):
		# Try with several sizes
		for torus_size in SpiNNakerTorusTests.TORUS_SIZES:
			self.generate_torus(*torus_size)
			
			# Get a dictionary of chips to their locations
			chips = {}
			for board in self.torus.boards.itervalues():
				for chip in board.chips.itervalues():
					chips[chip.get_mesh_position()] = chip
			
			# Check each chip is connected with their neighbours N, NE, W
			for pos, chip in chips.iteritems():
				for direction in [topology.NORTH, topology.NORTH_EAST, topology.WEST]:
					other_pos = topology.to_xy(
						topology.add_direction(topology.zero_pad(pos), direction))
					other_chip = chips[( other_pos[0]%(self.torus.width*12)
					                   , other_pos[1]%(self.torus.height*12)
					                   , )]
					
					other_direction = topology.opposite(direction)
					
					# Make sure we share links
					self.assertEqual(chip.get_in_link(direction),
					                 other_chip.get_out_link(other_direction))
					self.assertEqual(chip.get_out_link(direction),
					                 other_chip.get_in_link(other_direction))


if __name__=="__main__":
	unittest.main()
