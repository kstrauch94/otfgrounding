from typing import Dict, List, Any, Set
from collections import defaultdict

import otfgrounding.util as util
import re

# split on comma followed by whitespace except between ""
split_cons_re = r",\s+(?=[^()]*(?:\(|$))"

# split on comma except between ""
atom_name_re = r"(?P<name>\w+)\("
atom_params_re = r"(\w+)[,\)]"
class Propagator:

	__slots__ = []

	def __init__(self, line):
		pre_literals = re.split(split_cons_re, line.replace(":-","").strip()[:-1])
		print(pre_literals)
		for atom in pre_literals:
			s = re.search(atom_name_re, atom)
			print(s)
			print(s.group("name"))
			s = re.findall(atom_params_re, atom)
			print(s)


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