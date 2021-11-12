from clingo import parse_term
from clingo import ast

from typing import Dict, List, Any, OrderedDict, Set
from collections import defaultdict

import otfgrounding.util as util
from otfgrounding.data import AtomMapping, AtomMap
from otfgrounding.data import BodyType
from otfgrounding.data import VarToAtom
from otfgrounding.data import AtomTypes

from otfgrounding.atom_parts import Comparison
from otfgrounding.atom_parts import Literal

import logging


class PropagatorAST:

	amt = 0

	def __init__(self, body_parts):
		self.logger = logging.getLogger(self.__module__ + "." + self.__class__.__name__)

		PropagatorAST.amt += 1
		self.id = PropagatorAST.amt

		self.var_to_atom = VarToAtom()

		self.atom_types = AtomTypes()

		self.body_parts = body_parts

		self.signatures = set()

		self.ground_orders = {}

		for atom in self.body_parts[BodyType.pos_atom]:
			self.signatures.add((1, atom))

			atom_type = self.atom_types.add(atom)
			atom.assign_atom_type(atom_type)

		for atom in self.body_parts[BodyType.neg_atom]:
			self.signatures.add((-1, atom))

			atom_type = self.atom_types.add(atom)
			atom.assign_atom_type(atom_type)

		all_atoms = self.body_parts[BodyType.pos_atom] + self.body_parts[BodyType.neg_atom]

		for atom in all_atoms:
			# build an order on the positive atoms
			# slot comparison in the order of positive atoms
			# add the negative atoms at the end
			# results in a tuple:
			# (pos_atoms_ordered with dom comparisons slotted in, neg_atoms in whatever order)

			# if atom is a negative one
			# do the order of the positive ones first and append all of the other negative ones
			# at the end
			self.ground_orders[atom] = [self.slot_comparisons(self.order_with_starter(atom, [a for a in self.body_parts[BodyType.pos_atom] if a != atom]),
															  self.body_parts[BodyType.dom_comparison],
															  atom.vars)
										, [neg_atom for neg_atom in self.body_parts[BodyType.neg_atom] if neg_atom != atom]]
		



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

		my_comp = comparisons[:]

		for atom in order:
			avail_vars += atom.vars
			new_order.append(atom)

			for c in my_comp:
				can_slot = True
				for v in c.vars:
					if v not in avail_vars:
						can_slot = False

				if can_slot:
					new_order.append(c)

					my_comp.remove(c)

		return new_order

	def get_vars_vals(self, ground_atom_symbol, var_locs):

		vars_vals = {}
		for var in var_locs:
			ground_atom_args = ground_atom_symbol
			for loc in var.positions:
				ground_atom_args = ground_atom_args.arguments[loc]

			vars_vals[var.var] = str(ground_atom_args)

		return vars_vals

	@util.Timer("Time to init")
	def init(self, init):
		#import pprint
		#pp = pprint.PrettyPrinter()
		self.lits = set()

		lits = set()

		for sign, atom in self.signatures:
			name, arity = atom.name, atom.arity
			atom_type = self.atom_types.get_type(name, arity)

			var_locs = atom.var_loc()

			for ground_atom in init.symbolic_atoms.by_signature(name, arity):
				
				lit = init.solver_literal(ground_atom.literal) * sign
				AtomMapping.add(ground_atom.symbol, sign, lit)
				lits.add(lit)

				self.var_to_atom.add_atom(atom_type, ground_atom.symbol, self.get_vars_vals(ground_atom.symbol, var_locs))

		#pp.pprint(self.var_to_atom.vars_to_atom)
		#pp.pprint(AtomMapping.atom_2_lit)

		# TODO: do a function that "builds" the watches so I dont watch every single Literal
		# TODO: also, do a sort of mini propagation here

		for lit in lits:
			init.add_watch(lit)

		print("Init is DONE")

	@util.Count("Propagate")
	def propagate(self, control, changes):
		with util.Timer("Propagation-{}".format(str(self.id))):
			for c in changes:
				for ground_atom, sign in AtomMapping.get_atoms(c):
					name = ground_atom.name
					arity = len(ground_atom.arguments)
					
					if not self.atom_types.contains_atom(name, arity):
						continue

					atom_type = self.atom_types.get_type(name, arity)

					for atom_object in self.atom_types.get_atom(atom_type):
						if atom_object.sign != sign:
							continue

						
						order = self.ground_orders[atom_object]

						ng = [c]

						assignments = self.get_vars_vals(ground_atom, atom_object.var_loc())

						is_unit = False

						with util.Timer(f"ground-{self.id}"):
							if self.ground(order[0], order[1], ng, assignments, is_unit, control) is None:
								return None

	#@util.Count("ground")
	def ground(self, order_pos, order_neg, current_ng, current_assignment, is_unit, control):
		if order_pos == []:
			# do stuff with negative atoms
			if order_neg == []:
				# if we got here it means we found a unit or conflicting nogood and we should add it to the solver
				if not control.add_nogood(current_ng) or not control.propagate():
					return None
				
				return 1

			return self.ground_neg(order_neg, current_ng, current_assignment, is_unit, control)
			

		return self.ground_pos(order_pos, order_neg, current_ng, current_assignment, is_unit, control)

	#@profile
	def ground_pos(self, order_pos, order_neg, current_ng, current_assignment, is_unit, control):

		next_lit = order_pos[0]
		if isinstance(next_lit, Comparison):
			result = self.match_comparison(next_lit, current_assignment)
			if result == False:
				return 1

			if self.ground(order_pos[1:], order_neg, current_ng, current_assignment, is_unit, control) is None:
				return None

			return 1

		elif isinstance(next_lit, Literal):

			for match, lit, new_is_unit in self.get_next_lits(next_lit, current_assignment, is_unit, control):

				if match is None:
					continue

				# getting here means lit is true or the first unassigned one
				vars_vals = self.get_vars_vals(match, next_lit.var_loc())
				for k, v in current_assignment.items():
					vars_vals[k] = v

				if self.ground(order_pos[1:],
							order_neg,
							current_ng + [lit],
							vars_vals,
							new_is_unit,
							control) is None:

					return None
	
		return 1

	def ground_neg(self, order_neg, current_ng, current_assignment, is_unit, control):
		# if we are here we have to deal with the negative atoms
			

		# write function that can craft the atom based on the assignment
		# could also just use the match thing, just slower maybe?
		# function could just craft a "symbol" although it might be slow
		# converting a string to a symbol is slow
		# maybe its actually faster to use the intersection thing

		next_lit = order_neg[0]
		for match, lit, new_is_unit in self.get_next_lits(next_lit, current_assignment, is_unit, control):
			if match is None:
				#this means that the positive atom does not exist and hence
				# the negative one is true
				new_ng = current_ng
			else:
				new_ng = current_ng + [lit]

			if self.ground([],
						order_neg[1:],
						new_ng,
						current_assignment,
						new_is_unit,
						control) is None:
				return None

		return 1

	#@profile
	def get_next_lits(self, next_atom, current_assignment, is_unit, control):
		matches = self.match_pos_atom(next_atom, current_assignment)
		
		if len(matches) == 0:
			yield None, 0, is_unit
			return
		
		for match in matches:
			# for every match
			# grab lit of match
			new_is_unit = is_unit
			lit = AtomMapping.atom_2_lit[match, next_atom.sign]
			if control.assignment.value(lit) is None:
				if is_unit:
					continue
				
				new_is_unit = True 

			elif control.assignment.is_false(lit):
				continue

			yield match, lit, new_is_unit

	@util.Timer("Time to match pos atom")
	#@profile
	def match_pos_atom(self, atom, assignment):
		atom_sets = []

		for var, val in assignment.items():
			if var not in atom.vars:
				continue
			atoms = self.var_to_atom.atoms_by_var_val(atom.atom_type, var, val)

			if atoms is None:
				# if there is no atoms for a particular variable then the conflict cant exist
				# maybe have an internal data structure that keeps track of "impossible" variables?
				# if there is a propagation step with an impossible variable just do nothing
				# maybe also "unwatch" all atoms that have this impossible variable
				return set()

			atom_sets.append(atoms)

		if len(atom_sets) == 0:
			return set()
		return set.intersection(*atom_sets)

	@util.Timer("Time to match Comparison")
	def match_comparison(self, comparison, assignment):
		return comparison.eval(assignment)

	@util.Timer("Time to Check")
	def check(self, control):
		first_atom = self.body_parts[BodyType.pos_atom][0]
		order = self.ground_orders[first_atom]

		all_atoms = set()
		for var in first_atom.vars:
			all_atoms.update(self.var_to_atom.atoms_by_var(first_atom.atom_type, var))


		for ground_atom in all_atoms:
			vars_val = self.get_vars_vals(ground_atom, first_atom.var_loc())

			lit = AtomMapping.get_lit(ground_atom, first_atom.sign)
			if control.assignment.is_false(lit):
				continue

			if self.ground(order[0], order[1], [lit], vars_val, False, control) is None:
				return None
		
