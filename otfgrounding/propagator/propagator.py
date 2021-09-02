from clingo import parse_term

from typing import Dict, List, Any, Set
from collections import defaultdict

import otfgrounding.util as util
import re

# split on comma followed by whitespace except between ""
split_cons_re = r",\s+(?=[^()]*(?:\(|$))"

# split on comma except between ""
atom_name_re = r"(?P<name>\w+)\("
atom_params_re = r"(\w+)[,\)]"


class Atom:

	def __init__(self, name, variables):
		self.name = name
		self.variables = variables
		self.arity = len(variables)

	def __str__(self):
		return f"{self.name}{*self.variables,}".replace("'","")

class DomConstraint:

	def __init__(self, dom_c):
		self.dom_c = dom_c

	def test(self, variables):
		expression = self.dom_c

		for var,val in variables.items():
			print(var, val)
			expression = expression.replace(var,str(val))
			print(expression)

		print(expression)
		print(parse_term(expression))

class Propagator:

	def __init__(self, line):
		pre_literals = re.split(split_cons_re, line.replace(":-","").strip()[:-1])
		print(pre_literals)
		
		self.atoms = []
		
		self.all_vars = set()

		for atom in pre_literals:
			if any(c in ["=", ">", "<"] for c in atom):
				dc = DomConstraint(atom)
				dc.test({"D": 2, "D2": 1})

			s = re.search(atom_name_re, atom)
			name = s.group("name")

			variables = re.findall(atom_params_re, atom)
			
			atom = Atom(name, variables)

			print(atom)
			
			self.atoms.append(atom)
			self.all_vars.update(atom.variables)

		print(self.all_vars)


	@util.Timer("Prop_init")
	def init(self, init):
		pass

	@util.Count("Propagation")
	@util.Timer("Propagation")
	def propagate(self, control, changes):
		pass

	
	@util.Count("check")
	@util.Timer("check")
	def check(self, control):
		for tc in self.theory_constraints:
			if tc.check(control) is None:
				# check failed because there was a conflict
				return

class Domain:

	def __init__(self, atom):
		print(atom)
