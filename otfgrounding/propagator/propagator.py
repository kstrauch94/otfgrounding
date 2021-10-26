from clingo import parse_term
from clingo import ast

from typing import Dict, List, Any, OrderedDict, Set
from collections import defaultdict

import otfgrounding.util as util
from otfgrounding.data import AtomMapping, AtomMap
from otfgrounding.data import BodyType
from otfgrounding.data import VarToAtom
from otfgrounding.data import AtomTypes

import parse

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
				if val < max_val:
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

		import pprint
		pp = pprint.PrettyPrinter()
		print("a2l")
		pp.pprint(AtomMap.atom_2_lit)
		print("l2a")
		pp.pprint(AtomMap.lit_2_atom)

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

class PropagatorAST:

	def __init__(self, body_parts):

		self.var_to_atom = VarToAtom()

		self.atom_types = AtomTypes()

		self.body_parts = body_parts

		self.signatures = set()

		self.ground_orders = {}

		for i, atom in enumerate(self.body_parts[BodyType.pos_atom]):
			self.signatures.add((1, atom))

			atom_type = self.atom_types.add(atom.name, atom.arity, atom.var_loc())
			atom.assign_atom_type(atom_type)

		for i, atom in enumerate(self.body_parts[BodyType.neg_atom], start=i+1):
			self.signatures.add((-1, atom))

			self.atom_types.add(atom.name, atom.arity, atom.var_loc())

		all_atoms = self.body_parts[BodyType.pos_atom] + self.body_parts[BodyType.neg_atom]

		for atom in all_atoms:
			self.ground_orders[atom] = self.slot_comparisons(self.order_with_starter(atom, [a for a in all_atoms if a != atom]),
																					self.body_parts[BodyType.dom_comparison],
																					atom.vars)
		
		print("ldafhajkfhskjdfh")
		print(self.atom_types.atom_to_type)

		for a, o in self.ground_orders.items():
			print(a,o)

	def order_with_starter(self, starter, rest):
		if rest == []:
			return []

		counts = {}
		for atom in rest:
			for var in atom.vars:
				if var not in counts:
					counts[var] = 0
				counts[var] += 1

		for var in starter.vars:
			if var in counts:
				counts[var] -= 1


		best_atom = None
		best_val = None
		for atom in rest:
			val = 0
			for v in atom.vars:
				val += counts[v]

			if best_val is None:
				best_val = val
				best_atom = atom

			else:
				if val < best_val:
					best_val = val
					best_atom = atom

		new_rest = [a for a in rest if a != best_atom]
		return [best_atom] + self.order_with_starter(best_atom, new_rest)

	def slot_comparisons(self, order, comparisons, starter_vars):
		if comparisons == []:
			return order

		avail_vars = starter_vars

		new_order = []

		for atom in order:
			avail_vars += atom.vars
			new_order.append(atom)

			for c in comparisons:
				can_slot = True
				for v in c.vars:
					if v not in avail_vars:
						can_slot = False

				if can_slot:
					new_order.append(c)

					comparisons.remove(c)

		return new_order

	def get_vars_vals(self, ground_atom_symbol, var_locs):

		vars_vals = {}
		for var in var_locs:
			ground_atom_args = ground_atom_symbol
			for loc in var.positions:
				ground_atom_args = ground_atom_args.arguments[loc]

			vars_vals[var.var] = str(ground_atom_args)

		return vars_vals
	def init(self, init):
		import pprint
		pp = pprint.PrettyPrinter()
		lits = set()

		for sign, atom in self.signatures:
			name, arity = atom.name, atom.arity
			atom_type = self.atom_types.get_type(name, arity)

			parse_str = str(atom)
			var_locs = atom.var_loc()

			for ground_atom in init.symbolic_atoms.by_signature(name, arity):

				lit = init.solver_literal(ground_atom.literal) * sign
				AtomMapping.add(ground_atom.symbol, lit)
				lits.add(lit)

				symb_str = str(ground_atom.symbol)

				vars_vals = self.get_vars_vals(ground_atom.symbol, var_locs)

				self.var_to_atom.add_atom(atom_type, symb_str, vars_vals)

		#pp.pprint(self.var_to_atom.vars_to_atom)

		# TODO: do a function that "builds" the watches so I dont watch every single Literal
		# TODO: also, do a sort of mini propagation here

		for lit in lits:
			init.add_watch(lit)

		#print("a2l")
		#pp.pprint(AtomMapping.atom_2_lit)
		#print("l2a")
		#pp.pprint(AtomMap.lit_2_atom)

	def propagate(self, control, changes):
		for c in changes:
			print(c)
			for atom in AtomMapping.get_atoms(c):
				print(atom)
				name = atom.name
				arity = len(atom.arguments)
				
				if not self.atom_types.contains_atom(name, arity):
					continue

				atom_type = self.atom_types.get_type(name, arity)
				print("stuff: ", name, arity, atom_type)

				for _,_,var_loc in self.atom_types.get_atom(atom_type):
					print(var_loc)
					vars = tuple((loc.var for loc in var_loc))
					print(vars)
					vars_val = self.get_vars_vals(atom, var_loc)
					print(vars_val)
					
					order = self.ground_orders[name, vars]
					print(order)
					for o in order:
						self.match_atom(atom_type, vars_val)
			print()


	def get_atom_from(self, name, arity, vars):
		...

	def match_atom(self, atom_type, vars_val):
		atom_sets = []

		for var, val in vars_val.items():
			atoms = self.var_to_atom.atoms_by_var(atom_type, var, val)

			if atoms is None:
				continue

			atom_sets.append(atoms)

		print(atom_sets)

		print(set.intersection(*atom_sets))