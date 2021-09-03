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

	def __repr__(self):
		return str(self)

class DomConstraint:

	separate_re = r"(\W+)"
	
	separate_only_vars_re = r"\W+"

	def __init__(self, dom_c):
		self.dom_c = dom_c		

		self.separate()

		self.vars = re.split(DomConstraint.separate_only_vars_re, self.dom_c)
		
		self.vars = list(filter(lambda s: not s.isdigit(), self.vars))

		print(self.left, self.comparator, self.right)
		print(f"constraint variables: {self.vars}")

	def separate(self):

		separated = re.split(DomConstraint.separate_re, self.dom_c)

		self.left = []
		self.right = []
		self.comparator = None

		left = True
		for i in separated:
			if any(c in ["=", ">", "<"] for c in i):
				self.comparator = i.strip()
				left = False
				continue

			if left:
				self.left.append(i)
			else:
				self.right.append(i)

	def test(self, variables):
		for i in self.vars:
			if i not in variables:
				print(f"constraint variable {i} is not in the variables dictionary {variables}")
				raise Exception
		
		l = self.test_expression_side(self.left, variables)
		r = self.test_expression_side(self.right, variables)
		
		result = self.test_comparator(l, r)


	def test_comparator(self, l, r):
		if self.comparator == "=":
			return l == r
		if self.comparator == "!=":
			return l != r
		if self.comparator == ">":
			return l > r
		if self.comparator == ">=":
			return l >= r
		if self.comparator == "<":
			return l < r
		if self.comparator == "<=":
			return l <= r

	def test_expression_side(self, side, variables):
		new_side = []
		for i in side:
			if i in variables:
				new_side.append(str(variables[i]))
			else:
				new_side.append(i)
		
		return eval("".join(new_side))
		

class Propagator:

	def __init__(self, line):
		pre_literals = re.split(split_cons_re, line.replace(":-","").strip()[:-1])
		
		self.atoms = []
		
		self.all_vars = set()

		self.cons = []

		for atom in pre_literals:
			if any(c in ["=", ">", "<"] for c in atom):
				dc = DomConstraint(atom)
				dc.test({"D": 2, "D2": 1, "T": 10, "T2": 4})
				self.cons.append(dc)
			else:
				s = re.search(atom_name_re, atom)
				name = s.group("name")

				variables = re.findall(atom_params_re, atom)
				
				atom = Atom(name, variables)
				
				self.atoms.append(atom)
				self.all_vars.update(atom.variables)

		print(self.atoms)
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
		pass

class Domain:

	def __init__(self, atom):
		print(atom)
