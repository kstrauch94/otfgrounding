import logging
import os

from otfgrounding import util

from otfgrounding.propagator.propagator import PropagatorAST
from otfgrounding.propagator.propagator import Constraint

from otfgrounding.data import BodyType


from clingo.ast import parse_string
from clingo.symbol import String

from otfgrounding.inspect_ast import ConstraintInspector


class Handler:

	def __init__(self, cfile_contents) -> None:

		self.logger = logging.getLogger(self.__module__ + "." + self.__class__.__name__)

		self.cfile_contents = cfile_contents

	@util.Timer("Register")
	def register(self, prg) -> None:
		print("registering")
		constraints = []
		for line in self.cfile_contents.split("\n"):
			c_inspector = ConstraintInspector(prg)
			parse_string(line, c_inspector.inspect_constraint)

			if c_inspector.body_parts[BodyType.pos_atom] != []:
				constraints.append(Constraint(c_inspector.body_parts))

			
		prg.register_propagator(PropagatorAST(constraints))


	def __str__(self) -> str:
		return self.__class__.__name__
