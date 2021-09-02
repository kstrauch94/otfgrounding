import logging
import os

from otfgrounding import util

from otfgrounding.propagator.propagator import Propagator
from otfgrounding.propagator.propagator import Domain

theory_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../theory/untimed_theory.lp"))

class Handler:

	def __init__(self, cfile) -> None:

		self.logger = logging.getLogger(self.__module__ + "." + self.__class__.__name__)

		self.cfile = cfile

	@util.Timer("Register")
	def register(self, prg) -> None:
		print("registering")

		with open(self.cfile, "r") as f:
			for line in f.readlines():
				p = Propagator(line)

		#prg.register_propagator(self.propagator)
		

	def __str__(self) -> str:
		return self.__class__.__name__