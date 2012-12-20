#!/usr/bin/env python

"""
The system-wide parts of a spinnaker system.
"""


class SpiNNakerSystem(object):
	"""
	A network of SpiNNaker chips linked together.
	"""
	
	def __init__( self
	            , scheduler
	            , time_phase_period
	            ):
		"""
		time_phase_period is the duration of each time-phase.
		"""
		self.scheduler         = scheduler
		self.time_phase_period = time_phase_period
		
		# A list of all packets placed into the system
		self.packets = []
		
		self.time_phase = None
		self.advance_timephase()
	
	
	def advance_timephase(self):
		"""
		Advance to the next time phase.
		"""
		self.time_phase = {
			None: 0b00,
			0b00: 0b01,
			0b01: 0b11,
			0b11: 0b10,
			0b10: 0b00,
		}[self.time_phase]
		
		self.scheduler.do_later(self.advance_timephase, self.time_phase_period)

