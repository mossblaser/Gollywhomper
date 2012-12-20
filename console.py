#!/usr/bin/env python

"""
Utilities for printing experiment status on the console.

This is a mess... Sorry!
"""

import sys
import time

class Timer(object):
	"""
	A timer which prints
	"""
	TERMWIDTH = 80
	
	TIME_FORMAT = "%7.3fs"
	
	def __init__(self, console, action):
		self.console = console
		self.action  = action
		
		self.start = None
		self.end = None
		
		self.progress = None
		self.goal     = None
	
	
	def get_status_line(self, result = None):
		if result is None:
			success = "...."
		elif result == True:
			success = "DONE"
		else:
			success = "FAIL"
		
		if self.end is not None:
			time = Timer.TIME_FORMAT%(self.end-self.start)
		else:
			time = " "*len(Timer.TIME_FORMAT%0)
		
		tail = "[%s] %s"%(success, time)
		
		action_message = self.action
		if self.progress is not None and self.goal is None:
			action_message += " %s"%self.progress
		if self.progress is not None and self.goal is not None:
			action_message += " %d/%d"%(self.progress, self.goal)
			
			if self.end is not None and self.progress is not 0:
				delta = self.end - self.start
				total = delta * (float(self.goal) / float(self.progress))
				remain = total - delta
				action_message += " %s"%(Timer.TIME_FORMAT%remain)
		
		spaces = Timer.TERMWIDTH
		spaces -= len(tail)
		spaces -= len(action_message)
		space = " "*max(1, spaces)
		
		return "%s%s%s"%(action_message, space, tail)
	
	
	def __enter__(self):
		self.start = time.time()
		self.console.writeln(self.get_status_line())
		
		return self
	
	
	def __exit__(self, t,v,tb):
		self.end = time.time()
		
		self.progress = None
		self.goal     = None
		
		self.console.rewriteln(self.get_status_line(t is None))
		
		# Propagate the exception
		return False
	
	
	def set_progress(self, progress, goal = None):
		self.progress = progress
		self.goal     = goal or self.goal
		
		self.end = time.time()
		self.console.rewriteln(self.get_status_line())


class ExperimentConsole(object):
	"""
	Debug output console for the experiment
	"""
	
	def __init__(self):
		pass
	
	def timer(self, action):
		return Timer(self, action)
	
	
	def writeln(self, s):
		# Save the cursor position and write the line
		sys.stderr.write("%s\n"%s)
	
	
	def rewriteln(self, s):
		# Restore the cursor position, clear from there onward and rewrite the line
		# (ESC[3D is to recover from ^C when killed)
		sys.stderr.write("\033[1A\033[2D\033[K%s\n"%s)



