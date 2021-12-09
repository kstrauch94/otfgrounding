from clingo import parse_term
from clingo import ast
from clingo.symbol import parse_term

from typing import Dict, List, Any, OrderedDict, Set
from collections import defaultdict

import otfgrounding.util as util
from otfgrounding.data import AtomMapping
from otfgrounding.data import BodyType
from otfgrounding.data import AtomTypes
from otfgrounding.data import VarLocToAtom

from otfgrounding.atom_parts import Comparison
from otfgrounding.atom_parts import Literal

import logging


class PropagatorAST:

	amt = 0

	def __init__(self, body_parts):
		self.logger = logging.getLogger(self.__module__ + "." + self.__class__.__name__)

		PropagatorAST.amt += 1
		self.id = PropagatorAST.amt

		self.atom_types = AtomTypes()

		self.body_parts = body_parts

		self.signatures = set()

		self.ground_orders = {}

		self.impossible_vars = {}

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
			if atom.is_fact:
				continue
			# build an order on the positive atoms
			# slot comparison in the order of positive atoms
			# add the negative atoms at the end
			# results in a tuple:
			# (pos_atoms_ordered with dom comparisons slotted in, neg_atoms in whatever order)

			# if atom is a negative one
			# do the order of the positive ones first and append all of the other negative ones
			# at the end

			order = self.order_with_starter_and_containment(atom,
															[a for a in self.body_parts[BodyType.pos_atom] if a != atom],
															set(atom.variables.copy()))

			order = self.slot_comparisons(order, self.body_parts[BodyType.dom_comparison], atom.variables.copy())

			self.ground_orders[atom] = [order, [neg_atom for neg_atom in self.body_parts[BodyType.neg_atom] if neg_atom != atom]]

		print(self.ground_orders)

	def order_with_starter_and_containment(self, starter, rest, seen_vars):
		if rest == []:
			return []

		contained = []
		for atom in rest:
			if set(atom.variables).issubset(seen_vars):
				contained.append(atom)

		new_rest = [a for a in rest if a not in contained]

		if new_rest == []:
			return [(contained, None)]

		counts = {}
		for atom in new_rest:
			for var in atom.variables:
				if var not in counts:
					counts[var] = 0
				counts[var] += 1

		for var in seen_vars:
			if var in counts:
				counts[var] -= 1


		best_atom = None
		best_val = None
		for atom in new_rest:
			val = 0
			for v in atom.variables:
				val += counts[v]

			if best_val is None:
				best_val = val
				best_atom = atom

			else:
				if val < best_val:
					best_val = val
					best_atom = atom

		new_rest = [a for a in new_rest if a != best_atom]

		seen_vars.update(best_atom.variables)

		return [(contained, best_atom)] + self.order_with_starter_and_containment(best_atom, new_rest, seen_vars)

	def slot_comparisons(self, order, comparisons, starter_vars):
		if comparisons == []:
			return order

		avail_vars = set(starter_vars.copy())

		new_order = order.copy()

		my_comp = comparisons[:]

		to_remove = []
		for containment, atom in new_order:
			for c in my_comp:
				if set(c.variables).issubset(avail_vars):
					# can slot comparison for the avail vars BEFORE using
					# the next atom to ground
					containment.append(c)

					to_remove.append(c)
			my_comp = [c for c in my_comp if c not in to_remove]
			to_remove = []

			# Once we have appended all the comparison use the next atom
			# to ground to update the avail vars for the next run
			if atom is not None:
				avail_vars.update(atom.variables)

		return new_order

	def get_vars_vals(self, ground_atom_symbol, var_locs):

		vars_vals = {}
		for var in var_locs:
			ground_atom_args = ground_atom_symbol
			for loc in var.positions:
				ground_atom_args = ground_atom_args.arguments[loc]

			vars_vals[var] = str(ground_atom_args)

		return vars_vals

	@util.Timer("Time to init")
	def init(self, init):
		print("starting init")
		import pprint
		pp = pprint.PrettyPrinter()
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


				VarLocToAtom.add_atom(atom_type, ground_atom.symbol, self.get_vars_vals(ground_atom.symbol, var_locs))

		#pp.pprint(AtomMapping.atom_2_lit)
		#pp.pprint(AtomMapping.str_atom_2_lit)

		# TODO: do a function that "builds" the watches so I dont watch every single Literal
		# TODO: also, do a sort of mini propagation here

		for lit in lits:
			init.add_watch(lit)
		util.Count.add(f"watches {self.id}", len(lits))

		print("Init is DONE")

	@util.Count("Propagate")
	def propagate(self, control, changes):
		with util.Timer("Propagation-{}".format(str(self.id))):
			for c in changes:
				for ground_atom, sign in AtomMapping.get_atoms(c):
					name = ground_atom.name
					arity = len(ground_atom.arguments)

					# this part is here to check that the atom is relevant
					# to the constraint handled by this propagator
					if not self.atom_types.contains_atom(name, arity):
						continue

					atom_type = self.atom_types.get_type(name, arity)

					for atom_object in self.atom_types.get_atom(atom_type):
						if atom_object.is_fact:
							continue
						if atom_object.sign != sign:
							continue

						with util.Timer(f"ground-{self.id}-{str(atom_object)}"):

							if self.ground(self.ground_orders[atom_object][0],
											self.ground_orders[atom_object][1],
							 				[c],
											self.get_vars_vals(ground_atom, atom_object.var_loc()),
											False,
											control) is None:
								return None

	#@util.Count("ground")
	def ground(self, order_pos, order_neg, current_ng, current_assignment, is_unit, control):
		#print("ground call id", self.id, order_pos, order_neg, current_ng, current_assignment)
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



		contained, next_lit = order_pos[0]
		for atom in contained:
			if isinstance(atom, Comparison):
				result = self.match_comparison(atom, current_assignment)
				#print(current_assignment)
				#print(next_lit, result)
				if result == False:
					return 1


			if isinstance(atom, Literal):
				lit = self.match_contained_literal(atom, current_assignment)

				new_is_unit = self.test_lit_truth_val(lit, is_unit, control)
				if new_is_unit is None:
					return 1

				# update is_unit and append the lit to the current_ng
				is_unit = new_is_unit

				current_ng.append(lit)

		# after finishing the contained atoms ground the next lit

		if next_lit is None:
			# if the next lit is None we can continue to ground the negative atoms
			if self.ground(order_pos[1:],
						order_neg,
						current_ng,
						current_assignment,
						is_unit,
						control) is None:

				return None
		if isinstance(next_lit, Literal):
			#print("next: ", next_lit)
			#print(current_assignment)
			for match, lit, new_is_unit in self.get_next_lits(next_lit, current_assignment, is_unit, control):

				if match is None:
					#print("cont")
					continue
				#print("match ", match)
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
		#print("pos returnin 1")
		return 1

	def match_contained_literal(self, literal, assignment):

		literal_string = literal.eval(assignment)

		lit = AtomMapping.get_lit_from_str(literal_string, literal.sign)
		#symb = parse_term(literal_string)
		#lit = AtomMapping.get_lit(symb, literal.sign)

		return lit

	def ground_neg(self, order_neg, current_ng, current_assignment, is_unit, control):
		# if we are here we have to deal with the negative atoms


		# write function that can craft the atom based on the assignment
		# could also just use the match thing, just slower maybe?
		# function could just craft a "symbol" although it might be slow
		# converting a string to a symbol is slow
		# maybe its actually faster to use the intersection thing
		"""
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
		"""
		for literal in order_neg:
			lit = self.match_contained_literal(literal, current_assignment)

			new_is_unit = self.test_lit_truth_val(lit, is_unit, control)
			if new_is_unit is None:
				return 1

			# update is_unit and append the lit to the current_ng
			is_unit = new_is_unit

			current_ng.append(lit)

		if self.ground([],
					[],
					current_ng,
					current_assignment,
					is_unit,
					control) is None:
			return None

		return 1

	#@profile
	def get_next_lits(self, next_atom, current_assignment, is_unit, control):
		#print("get lits")
		matches = self.match_pos_atom(next_atom, current_assignment)
		#print("match count: ", len(matches))
		if len(matches) == 0:
			yield None, 0, is_unit
			return

		for match in matches:
			# for every match
			# grab lit of match
			new_is_unit = is_unit
			lit = AtomMapping.atom_2_lit[match, next_atom.sign]

			new_is_unit = self.test_lit_truth_val(lit, is_unit, control)
			if new_is_unit is None:
				continue

			yield match, lit, new_is_unit

	def test_lit_truth_val(self, lit, is_unit, control):
		# return value is either None of bool
		# if None then the nogood is useless with this literal
		# if bool then that is the new value for is_unit
		if control.assignment.value(lit) is None:
			if is_unit:
				return None

			return True

		elif control.assignment.is_false(lit):
			return None

		return is_unit

	@util.Timer("Time to match pos atom")
	#@profile
	def match_pos_atom(self, atom, assignment):
		atom_sets = []

		for var, val in assignment.items():
			if var.var not in atom.variables:
				continue

			atoms = VarLocToAtom.atoms_by_var_val(atom.atom_type, atom.varinfo_for_var(var.var), val)
			#print(atoms)

			if atoms is None:
				# if there is no atoms for a particular variable then the conflict cant exist
				# maybe have an internal data structure that keeps track of "impossible" variables?
				# if there is a propagation step with an impossible variable just do nothing
				# maybe also "unwatch" all atoms that have this impossible variables
				return set()

			atom_sets.append(atoms)
		"""
		no_atoms_in_assignment = True

		for k in assignment:
			if k.var in atom.variables:
				no_atoms_in_assignment = False
				break

		if no_atoms_in_assignment:
			if len(atom_sets) == 0:
				all_atoms = set()
				for var in atom.variables:
					all_atoms.update(VarLocToAtom.atoms_by_var(atom.atom_type, atom.varinfo_for_var(var)))
				return all_atoms



		atoms = set()
		var_locs = atom.var_loc()
		for symbol, sign in AtomMapping.atom_2_lit.keys():
			if sign != atom.sign or symbol.name != atom.name or len(symbol.arguments) != atom.arity:
				continue

			for k, v in self.get_vars_vals(symbol, var_locs).items():
				if k in assignment:
					no_atoms_in_assignment = False
					if v == assignment[k]:
						atoms.add(symbol)

		return atoms
		"""

		# this part here handles when an atom has no variables in the assignment
		if len(atom_sets) == 0:
			all_atoms = set()
			for var in atom.variables:
				all_atoms.update(VarLocToAtom.atoms_by_var(atom.atom_type, atom.varinfo_for_var(var)))
			return all_atoms

		with util.Timer("intersection"):
			sec = set.intersection(*atom_sets)

		return sec

	@util.Timer("Time to match Comparison")
	def match_comparison(self, comparison, assignment):
		return comparison.eval(assignment)

	@util.Timer("Time to Check")
	def check(self, control):
		first_atom = self.body_parts[BodyType.pos_atom][0]
		order = self.ground_orders[first_atom]

		all_atoms = set()
		for var in first_atom.variables:
			all_atoms.update(VarLocToAtom.atoms_by_var(first_atom.atom_type, first_atom.varinfo_for_var(var)))

		for ground_atom in all_atoms:
			vars_val = self.get_vars_vals(ground_atom, first_atom.var_loc())

			lit = AtomMapping.get_lit(ground_atom, first_atom.sign)
			if control.assignment.is_false(lit):
				continue

			if self.ground(order[0], order[1], [lit], vars_val, False, control) is None:
				return None
