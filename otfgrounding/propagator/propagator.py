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

class Constraint:

	def __init__(self, body_parts) -> None:
		self.body_parts = body_parts

		self.ground_orders = {}

		self.all_atoms = self.body_parts[BodyType.pos_atom] + self.body_parts[BodyType.neg_atom]

		for atom in self.all_atoms:
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


class PropagatorAST:

	amt = 0

	def __init__(self, constraints):
		self.logger = logging.getLogger(self.__module__ + "." + self.__class__.__name__)

		self.constraints = constraints

		self.watches = {}

		self.domains = {}

	@util.Timer("Time to init")
	def init(self, init):
		print("starting init")

		for index, constraint in enumerate(self.constraints):
			for atom in constraint.all_atoms:
				self.domains[(atom.name, atom.arity)] = {}
				# if atom is a fact still add it to the domains but do not add watches or anything like that
				if atom.is_fact:
					continue
				for symb_atom in init.symbolic_atoms.by_signature(atom.name, atom.arity):
					solver_lit = init.solver_literal(symb_atom.literal) * atom.sign
					watch = (index, symb_atom.symbol, atom)
					self.watches.setdefault(solver_lit, []).append(watch)

		
		for (name, arity), atoms in self.domains.items():
			for symb_atom in init.symbolic_atoms.by_signature(name, arity):
				atoms[symb_atom.symbol] = init.solver_literal(symb_atom.literal)

		for lit in self.watches.keys():
			init.add_watch(lit)

		util.Count.add("watches", len(self.watches.keys()))

		print("Init is DONE")

	@util.Count("Propagate")
	@util.Timer("Propagate")
	def propagate(self, control, changes):
		for c in changes:
			for index, symbol, atom in self.watches[c]:
				ground_order = self.constraints[index].ground_orders[atom]
				with util.Timer(f"ground"):
					assignment = {}
					atom.match(symbol, assignment, []),
					if self.ground(ground_order[0],
									ground_order[1],
									[c],
									assignment,
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
					#print("adding constraint", current_assignment)
					return None

				return 1

			return self.ground_neg(order_neg, current_ng, current_assignment, is_unit, control)


		return self.ground_pos(order_pos, order_neg, current_ng, current_assignment, is_unit, control)

	#@profile
	def ground_pos(self, order_pos, order_neg, current_ng, current_assignment, is_unit, control):



		contained, next_lit = order_pos[0]
		contained_lit_added = 0
		
		for atom in contained:
			if isinstance(atom, Comparison):
				result = self.match_comparison(atom, current_assignment)
				#print(current_assignment)
				#print(next_lit, result)
				if result == False:
					return 1


			if isinstance(atom, Literal):
				#print("contained lit")
				#print(current_assignment)
				#print(atom)
				lit = self.match_contained_literal(atom, current_assignment)

				new_is_unit = self.test_lit_truth_val(lit, is_unit, control)
				if new_is_unit is None:
					for i in range(contained_lit_added):
						current_ng.pop()
					return 1

				# update is_unit and append the lit to the current_ng
				is_unit = new_is_unit

				current_ng.append(lit)
				contained_lit_added += 1

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
			domain = self.domains[next_lit.signature()]
			for symb in domain:
				bound = []
				if next_lit.match(symb, current_assignment, bound):
					#print("match ", symb)
					lit = domain[symb]
					new_is_unit = self.test_lit_truth_val(lit, is_unit, control)
					if new_is_unit is None:
						for var in bound:
							del current_assignment[var]
						continue

					# update is_unit and append the lit to the current_ng
					is_unit = new_is_unit

					current_ng.append(lit)

					if self.ground(order_pos[1:],
								order_neg,
								current_ng,
								current_assignment,
								new_is_unit,
								control) is None:

						return None
					
					current_ng.pop()

				for var in bound:
					del current_assignment[var]
		
		# pop the added contained lits
		for i in range(contained_lit_added):
			current_ng.pop()
		return 1

	def match_contained_literal(self, literal, assignment):

		literal_string = literal.eval(assignment)

		#lit = AtomMapping.get_lit_from_str(literal_string, literal.sign)
		symb = parse_term(literal_string)
		
		if symb not in self.domains[literal.signature()]:
			return -1
		
		return self.domains[literal.signature()][symb] * literal.sign

	def ground_neg(self, order_neg, current_ng, current_assignment, is_unit, control):
		# if we are here we have to deal with the negative atoms


		# write function that can craft the atom based on the assignment
		# could also just use the match thing, just slower maybe?
		# function could just craft a "symbol" although it might be slow
		# converting a string to a symbol is slow
		# maybe its actually faster to use the intersection thing
		neg_lit_added = 0
		for literal in order_neg:
			lit = self.match_contained_literal(literal, current_assignment)

			new_is_unit = self.test_lit_truth_val(lit, is_unit, control)
			if new_is_unit is None:
				for i in range(neg_lit_added):
					current_ng.pop()
				return 1

			# update is_unit and append the lit to the current_ng
			is_unit = new_is_unit

			current_ng.append(lit)
			neg_lit_added += 1

		if self.ground([],
					[],
					current_ng,
					current_assignment,
					is_unit,
					control) is None:
			return None

		for i in range(len(order_neg)):
			current_ng.pop()

		return 1

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

	@util.Timer("Time to match Comparison")
	def match_comparison(self, comparison, assignment):
		return comparison.eval(assignment)

	@util.Timer("Time to Check")
	def check(self, control):
		#print("check start")
		for constraint in self.constraints:
			first_atom = constraint.body_parts[BodyType.pos_atom][0]
			#print(first_atom)
			order = constraint.ground_orders[first_atom]
			#print("using ", first_atom, order)
			#print(first_atom.signature())
			domain = self.domains[first_atom.signature()]
			#print(domain)

			for ground_atom in domain:
				#print(f"check {ground_atom}")
				assignment = {}
				first_atom.match(ground_atom, assignment, [])

				lit = domain[ground_atom]
				if control.assignment.is_false(lit):
					continue

				if self.ground(order[0], order[1], [lit], assignment, False, control) is None:
					return None
		
		#print("Check succesful")
