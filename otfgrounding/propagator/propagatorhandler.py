import logging
import os

from otfgrounding import util

from otfgrounding.propagator.propagator import PropagatorAST
from otfgrounding.data import BodyType


from clingo.ast import parse_string

from otfgrounding.inspect_ast import ConstraintInspector


class Handler:

	def __init__(self, cfile) -> None:

		self.logger = logging.getLogger(self.__module__ + "." + self.__class__.__name__)

		self.cfile = cfile

	@util.Timer("Register")
	def register(self, prg) -> None:
		print("registering")

		with open(self.cfile, "r") as f:
			for line in f.readlines():
				c_inspector = ConstraintInspector()
				parse_string(line, c_inspector.inspect_constraint)

				if c_inspector.body_parts[BodyType.pos_atom] != []:
					p = PropagatorAST(c_inspector.body_parts)

					prg.register_propagator(p)


	def __str__(self) -> str:
		return self.__class__.__name__
