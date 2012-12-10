#!/usr/bin/env python

"""
Utilities for working with the hexagonal toroidal-mesh topology used in
SpiNNaker.

This uses the addressing scheme suggested in

Addressing and Routing in Hexagonal Networks with Applications for Tracking
Mobile Users and Connection Rerouting in Cellular Networks by Nocetti et. al.

With the "z" dimension omitted (and assumed to be zero). X points from
left-to-right, Y points from bottom-to-top and Z points from
top-right-to-bottom-left.
"""

EAST       = 0
NORTH_EAST = 1
NORTH      = 2
WEST       = 3
SOUTH_WEST = 4
SOUTH      = 5


def manhattan(vector):
	"""
	Calculate the Manhattan distance required to traverse the given vector.
	"""
	return sum(map(abs, vector))


def median_element(values):
	"""
	Returns the value of the median element of the set.
	"""
	return sorted(values)[len(values)/2]


def to_shortest_path(vector):
	"""
	Converts a vector into the shortest-path variation.
	
	A shortest path has at least one dimension equal to zero and the remaining two
	dimensions have opposite signs (or are zero).
	"""
	assert(len(vector) == 3)
	
	# The vector (1,1,1) has distance zero so this can be added or subtracted
	# freely without effect on the destination reached. As a result, simply
	# subtract the median value from all dimensions to yield the shortest path.
	median = median_element(vector)
	return tuple(v - median for v in vector)


def get_path(src, dst, bounds = None):
	"""
	Gets the shortest path from src to dst.
	
	If bounds is given it must be a 2-tuple specifying the (x,y) dimensions of the
	mesh size. The path will then be allowed to 'wrap-around', otherwise it will
	not.
	"""
	assert(len(src) == len(dst) == 3)
	assert(bounds is None or len(bounds) == 2)
	
	# If bounded, re-centre the world around the source
	if bounds is not None:
		dst = ( ((dst[0] - src[0]) + bounds[0]/2)   % bounds[0]
		      , ((dst[1] - src[1]) + bounds[1]/2)   % bounds[1]
		      , ((dst[2] - src[2]) + min(bounds)/2) % min(bounds)
		      )
		src = ( bounds[0]/2
		      , bounds[1]/2
		      , min(bounds)/2
		      )
	
	
	# The path is simply a delta of the source and destination
	delta = tuple(d-s for (s,d) in zip(src, dst))
	
	# Return the shortest path to the given point
	return to_shortest_path(delta)


def zero_pad(vector, length = 3):
	"""
	Zero pad a vector to the required length.
	"""
	return tuple((list(vector) + ([0]*length))[:length])
