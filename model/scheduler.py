#!/usr/bin/env python

"""
A Verilog-style discrete-time scheduler.
"""

from collections import defaultdict

class Scheduler(object):
	"""
	A scheduler with three queues:
	 * Ready: tasks which are ready to be run and may be executed in any order.
	 * Inactive: tasks which can run once all ready tasks have been executed.
	 * Postponed: Tasks which should run at some point in the future
	"""
	
	def __init__(self):
		self.clock = 0
		
		self.ready     = []
		self.inactive  = []
		self.postponed = defaultdict(list)
	
	
	def do_now(self, c):
		"""
		Add the callable c to the ready queue.
		"""
		self.ready.append(c)
	
	
	def do_later(self, c, delay = 0):
		"""
		Call the callable c after delay cycles. If the number of cycles is zero the
		callable will be added to the inactive queue. Otherwise it will be added to
		the postponed queue.
		"""
		
		assert(delay >= 0)
		
		if delay == 0:
			self.inactive.append(c)
		else:
			self.postponed[self.clock + delay].append(c)
	
	
	def run(self):
		"""
		Run the scheduler. Returns when no further tasks are due to be executed.
		Yields the current clock value after each call to a task.
		"""
		
		while self.ready or self.inactive or self.postponed:
			while self.ready or self.inactive:
				# Execute ready tasks
				while self.ready:
					self.ready.pop(0)()
					yield self.clock
				
				# Make inactive tasks ready to run (edge-case: unless someone added a
				# ready task while we were yielded...)
				if not self.ready:
					self.ready    = self.inactive
					self.inactive = []
			
			# Advance the clock to the next set of postponed tasks and mark them as
			# ready to run
			if self.postponed:
				self.clock = min(self.postponed.iterkeys())
				self.ready = self.postponed.pop(self.clock)
			else:
				return
