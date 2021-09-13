from clingo import parse_term

from typing import Dict, List, Any, Set
from collections import defaultdict

import otfgrounding.util as util
from otfgrounding.data import AtomMap

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

	def substitution(self, args):
		subs = {}
		for i in range(self.arity):
			v = self.variables[i]
			arg = args[i]
			subs[v] = arg

		return subs

	def partial_sub(self, variables):
		subs = {}
		for i in range(self.arity):
			v = self.variables[i]
			arg = args[i]
			subs[v] = arg

		return arg

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

		print(self)
		#print(f"constraint variables: {self.vars}")

	def separate(self):

		separated = re.split(DomConstraint.separate_re, self.dom_c)

		self.left = []
		self.right = []
		self.operator = None

		left = True
		for i in separated:
			if any(c in ["=", ">", "<"] for c in i):
				self.operator = i.strip()
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
			if variables[i] is None:
				print(f"variable {i} has a None value. Can not continue.")
				return None
		
		l = self.test_expression_side(self.left, variables)
		r = self.test_expression_side(self.right, variables)
		
		result = self.test_operator(l, r)

		return result

	def test_operator(self, l, r):
		if self.operator == "=":
			return l == r
		if self.operator == "!=":
			return l != r
		if self.operator == ">":
			return l > r
		if self.operator == ">=":
			return l >= r
		if self.operator == "<":
			return l < r
		if self.operator == "<=":
			return l <= r

	def test_expression_side(self, side, variables):
		new_side = []
		for i in side:
			if i in variables:
				new_side.append(str(variables[i]))
			else:
				new_side.append(i)
		
		return eval("".join(new_side))

	def __str__(self):
		return str(self.left) + str(self.operator) + str(self.right)
		


class Propagator:

	def __init__(self, line):
		pre_literals = re.split(split_cons_re, line.replace(":-","").strip()[:-1])

		self.atoms = {}
		
		self.all_vars = set()

		self.cons = []

		for atom in pre_literals:
			if any(c in ["=", ">", "<"] for c in atom):
				dc = DomConstraint(atom)
				self.cons.append(dc)
			else:
				s = re.search(atom_name_re, atom)
				name = s.group("name")

				variables = re.findall(atom_params_re, atom)
				
				atom = Atom(name, variables)
				
				self.atoms[atom.name, atom.arity] = atom
				self.all_vars.update(atom.variables)

		print(self.atoms)
		print(self.all_vars)

		self.var_assignment = {}
		for v in self.all_vars:
			self.var_assignment[v] = None


	def ordering(self, atoms):
		for atom in atoms:
			pass
	
	def order_with_starter(self, starter, rest):
		if rest == []:
			return [starter]

		counts = {}
		for atom in rest:
			for var in atom.variables:
				if var not in counts:
					counts[var] = 0
				counts[var] += 1

		for var in starter.variables:
			if var in counts:
				counts[var] -= 1


		max_atom = None
		max_val = None
		for atom in rest:
			val = 0
			for v in atom.variables:
				val += counts[v]
			
			if max_val is None:
				max_val = val
				max_atom = atom
			
			else:
				if val > max_val:
					max_val = val
					max_atom = atom
			
		new_rest = [a for a in rest if a != max_atom]
		return [max_atom] + self.order_with_start(max_atom, new_rest)

	@util.Timer("Prop_init")
	def init(self, init):


		lits = set()

		for atom in self.atoms:
			name, arity = atom
			for symb in init.symbolic_atoms.by_signature(name, arity):
				lit = init.solver_literal(symb.literal)
				AtomMap.add(symb.symbol, lit)
				lits.add(lit)
			
		for lit in lits:
			init.add_watch(lit)

		#import pprint
		#pp = pprint.PrettyPrinter()
		#pp.pprint(AtomMap.atom_2_lit)
		#print(AtomMap.lit_2_atom)

	@util.Count("Propagation")
	@util.Timer("Propagation")
	def propagate(self, control, changes):
		for lit in changes:
			for atom in AtomMap.lit_2_atom[lit]:
				self.prop(control, atom, lit)

	
	def prop(self, control, atom, lit):
		self.reset_assignment()
		name, arity, args = atom
		if (name, arity) not in self.atoms:
			return

		self.var_assignment.update(self.atoms[name, arity].substitution(args))

		ng = [lit]
		found_unassigned = False

		for atom in self.atoms:
			# if the atom is not the one we started with:
			if atom != (name, arity):
				pass

	def reset_assignment(self):
		for v in self.var_assignment:
			self.var_assignment[v] = None

	@util.Count("check")
	@util.Timer("check")
	def check(self, control):
		pass

