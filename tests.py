#!/usr/bin/env python

"""
Unit tests. Not comprehensive but just quick and dirty...
"""

import unittest

from scheduler import Scheduler

from link import SilistixLink
from link import DeadLink
from link import BufferLink

from system import SpiNNakerSystem

from packet import SpiNNakerP2PPacket

from router import SpiNNakerRouter

from core import SpiNNakerTrafficGenerator

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
		                             , RouterTests.MESH_DIMENSIONS
		                             , RouterTests.MESH_POSITION
		                             , self.injection_link
		                             , self.exit_link
		                             , self.in_links
		                             , self.out_links
		                             , RouterTests.ROUTER_PERIOD
		                             , RouterTests.WAIT_BEFORE_EMERGENCY
		                             , RouterTests.WAIT_BEFORE_DROP
		                             )
	
	
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
		self.assertEqual(self.router.counters["packet_routed"], 0)
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
		self.assertEqual(self.router.counters["packet_routed"], 1)
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
			self.assertEqual(self.router.counters["packet_routed"], 1)
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
			self.assertEqual(self.router.counters["packet_routed"], 0)
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
			self.assertEqual(self.router.counters["packet_routed"], 1)
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
			self.assertEqual(self.router.counters["packet_routed"], 0)
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
		                              , (100,100)
		                              , (50,50)
		                              )
		
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
		                              , (100,100)
		                              , (50,50)
		                              , 10
		                              )
		
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
		                              , (100,100)
		                              , (50,50)
		                              )
		
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
		                              , (100,100)
		                              , (50,50)
		                              , 10
		                              )
		
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
	


if __name__=="__main__":
	unittest.main()
