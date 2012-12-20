#!/usr/bin/env python

"""
Top level experiment class. Can be inherited and extended to perform
measurements etc.

This is a mess... Sorry!
"""


from console import ExperimentConsole

import inspect

from model.scheduler import Scheduler
from model.system    import SpiNNakerSystem
from model.top       import SpiNNakerTorus


class Simulation(object):
	
	# The simulator will run at 150MHz
	
	TIME_PHASE_PERIOD = 10000
	
	WIDTH  = 1
	HEIGHT = 1
	
	# Use S-ATA links between boards?
	USE_SATA_LINKS = True
	
	# The FPGA accepts one packet every cycle... probably...
	SATA_ACCEPT_PERIOD = 1
	
	# S-ATA link probably negledgable but we have 6GBit/s
	# link which is 1 150MHz cycle for 32bits and frames
	# with 8 packets in are 12 32bit words so 12 cycles
	# per frame. Four stage pipeline at each FPGA to
	# produce and extract frames. This may be optimistic
	SATA_LATENCY = 12 + 4 + 4
	
	# Not really sure what to make this, as such I'm just giving it one buffer
	# entry for each cycle of sata latency...
	SATA_BUFFER_LENGTH = 12 + 4 + 4
	
	SILISTIX_SEND_CYCLES = 23 # 250MBit/s (24 cycles per 40 bit word)
	SILISTIX_ACK_CYCLES  = 1
	
	INJECTION_BUFFER_LENGTH = 4
	
	ROUTER_PERIOD         = 1 # 150MHz
	WAIT_BEFORE_EMERGENCY = 240   # This or 4096 depending on the tool...
	WAIT_BEFORE_DROP      = 240*2
	
	CORE_PERIOD  = 1 # 150MHz
	PACKET_PROB  = 0.01
	DISTANCE_STD = None
	
	
	class StopExperiment(Exception):
		pass
	
	
	def __init__(self, resultfile_prefix=""):
		self.console = ExperimentConsole()
		
		with self.console.timer("Initialising simulation..."):
			self.scheduler = Scheduler()
			self.system    = SpiNNakerSystem( self.scheduler
			                                , Simulation.TIME_PHASE_PERIOD)
			self.torus     = SpiNNakerTorus( self.scheduler
			                               , self.system
			                               , Simulation.WIDTH
			                               , Simulation.HEIGHT
			                               , Simulation.USE_SATA_LINKS
			                               , Simulation.SATA_ACCEPT_PERIOD
			                               , Simulation.SATA_BUFFER_LENGTH
			                               , Simulation.SATA_LATENCY
			                               , Simulation.SILISTIX_SEND_CYCLES
			                               , Simulation.SILISTIX_ACK_CYCLES
			                               , Simulation.INJECTION_BUFFER_LENGTH
			                               , Simulation.ROUTER_PERIOD
			                               , Simulation.WAIT_BEFORE_EMERGENCY
			                               , Simulation.WAIT_BEFORE_DROP
			                               , Simulation.CORE_PERIOD
			                               , Simulation.PACKET_PROB
			                               , Simulation.DISTANCE_STD
			                               )
		
		self.resultfile_prefix = resultfile_prefix
		
		# A set of functions which are expected to be generators which are initially
		# called with an argument of a file to use to store results. The generator's
		# .next() is called every simulation cycle with a boolean indicating if the
		# cycle was the first of a new clock cycle. At the end of the simulation,
		# a StopExperiment is raised in the generator
		self.measurements = []
		for name, f in inspect.getmembers(self, predicate=inspect.ismethod):
			if name.startswith("measurement_"):
				self.measurements.append(f)
	
	
	def measurement_simulator_load(self, datafile):
		"""
		Measure the number of steps the simulator is executing for each clock cycle
		"""
		# Set up
		datafile.write("#clock number_of_steps\n") 
		yield
		
		# Measure how much work the simulator is doing
		step = 0
		try:
			while True:
				if (yield):
					datafile.write("%d %d\n"%(self.scheduler.clock, step))
					step = 0
				else:
					step += 1
		except Simulation.StopExperiment:
			pass
			# Nothing to write at the end of simulation
		
	
	
	def run(self, num_clock_cycles):
		# Get the iterator for the scheduler
		it = self.scheduler.run()
		
		# Start all the (measurer, file, name) and open their files
		gen_files = []
		for measurement in self.measurements:
			# A little introspection to get the function name
			name = measurement.__name__.partition("measurement_")[2]
			
			# Open a file [prefix][function name].log to store the results of that
			# measurer
			f = open("%s%s.log"%(self.resultfile_prefix, name),"w")
			
			# Start the measurer
			with self.console.timer("Initialising measurer '%s'..."%name):
				g = measurement(f)
				g.next()
			
			# Put the running measurer and its file into the dictionary...
			gen_files.append((g, f, name))
		
		# Store the last observed clock value to allow us to detect when it changes
		with self.console.timer("Running simulation...") as timer:
			clock = 0
			timer.set_progress(clock, num_clock_cycles)
			
			# Run the experiment for the prescribed number of cycles
			while it.next() < num_clock_cycles:
				# Has the clock changed?
				clock_changed = clock != self.scheduler.clock
				clock = self.scheduler.clock
				
				# Some progress output
				if (clock_changed and clock%10 == 0):
					timer.set_progress(clock, num_clock_cycles)
				
				# Run each measurer informing it if the clock changed
				for gen, _, _ in gen_files:
					gen.send(clock_changed)
		
		# Terminate each measurer
		for gen, f, name in gen_files:
			with self.console.timer("Finalising measurer '%s'..."%name):
				try:
					gen.throw(Simulation.StopExperiment())
				except StopIteration:
					pass
				f.close()
		


if __name__=="__main__":
	s = Simulation()
	s.run(1000)
