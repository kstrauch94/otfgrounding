from clingo import ast

from typing import Dict, List, Any, OrderedDict, Set
from collections import defaultdict

import otfgrounding.util as util
from otfgrounding.data import AtomMapping
from otfgrounding.data import BodyType
from otfgrounding.data import VarLocToAtom

from otfgrounding.atom_parts import Comparison
from otfgrounding.atom_parts import Literal

import logging

class Memoize:
	def __init__(self, fn):
		self.fn = fn
		self.memo = {}
	def __call__(self, *args):
		new_args = []
		for i, arg in enumerate(args):
			if type(arg) == dict:
				new_args.append(tuple(arg.items()))
			else:
				new_args.append(arg)
		new_args = tuple(new_args)
		if new_args not in self.memo:
			self.memo[new_args] = self.fn(*args)
		return self.memo[new_args]

class Constraint:

	def __init__(self, body_parts):
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

			print("slotting comparisons:", self.body_parts[BodyType.dom_comparison])
			order = self.slot_comparisons(order, self.body_parts[BodyType.dom_comparison], atom.variables.copy())
			print(order)

			self.ground_orders[atom] = [order, [neg_atom for neg_atom in self.body_parts[BodyType.neg_atom] if neg_atom != atom]]

		print(self.ground_orders)


	def order_with_starter_and_containment(self, starter, rest, seen_vars):
		if rest == []:
			return [([], None)]

		contained = []
		for atom in rest:
			if set(atom.variables).issubset(seen_vars):
				contained.append(atom)

		new_rest = [a for a in rest if a not in contained]

		if new_rest == []:
			return [(contained, None)]

		#new_rest, best_atom = self.get_new_rest_counts(new_rest, seen_vars)
		new_rest, best_atom = self.new_rest_by_score(new_rest, seen_vars)

		seen_vars.update(best_atom.variables)

		return [(contained, best_atom)] + self.order_with_starter_and_containment(best_atom, new_rest, seen_vars)

	def new_rest_by_score(self, new_rest, seen_vars):

		best_atom = None
		best_score = None

		for atom in new_rest:
			if best_atom is None:
				best_atom = atom
				best_score = atom.score(seen_vars)
			else:
				if best_score <= atom.score(seen_vars):
					continue

				best_score = atom.score(seen_vars)
				best_atom = atom

		return [a for a in new_rest if a != best_atom], best_atom
		

	def new_rest_counts(self, new_rest, seen_vars):
		# uses the amount of atoms the variables in the atom will affect when instantiated
		#e.g. given a the atoms o(B,N,M)
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

		return [a for a in new_rest if a != best_atom], best_atom

	def slot_comparisons(self, order, comparisons, starter_vars):
		print("using ", order, "to slot")
		if comparisons == []:
			return order

		avail_vars = set(starter_vars.copy())

		new_order = order.copy()

		my_comp = comparisons.copy()

		to_remove = []
		for containment, atom in new_order:
			print("checking for slotting with ", avail_vars)
			for c in my_comp:
				if set(c.variables).issubset(avail_vars):
					# can slot comparison for the avail vars BEFORE using
					# the next atom to ground
					containment.append(c)
					print("slotted ", c)

					to_remove.append(c)
			my_comp = [c for c in my_comp if c not in to_remove]
			to_remove = []

			# Once we have appended all the comparison use the next atom
			# to ground to update the avail vars for the next run
			if atom is not None:
				print("updating ", avail_vars, "with ", atom.variables)
				avail_vars.update(atom.variables)
			else:
				print("atom is None", None)
			print("left comps after slotting here", my_comp)

		return new_order


class PropagatorAST:

	amt = 0

	def __init__(self, constraints):
		self.logger = logging.getLogger(self.__module__ + "." + self.__class__.__name__)

		self.constraints = constraints
		
		self.watches = {}

	@util.Timer("varsvals")
	def get_vars_vals(self, ground_atom_symbol, var_locs):

		vars_vals = {}
		for var in var_locs:
			ground_atom_args = ground_atom_symbol
			for loc in var.positions:
				ground_atom_args = ground_atom_args.arguments[loc]

			vars_vals[var] = ground_atom_args

		return vars_vals

	@util.Timer("Time to init")
	def init(self, init):
		print("starting init")
		domains = set()
		for index, constraint in enumerate(self.constraints):
			for atom in constraint.all_atoms:
				domains.add((atom.name, atom.arity, atom))
				# if atom is a fact still add it to the domains but do not add watches or anything like that
				if atom.is_fact:
					continue
				for symb_atom in init.symbolic_atoms.by_signature(atom.name, atom.arity):
					solver_lit = init.solver_literal(symb_atom.literal) * atom.sign
					watch = (index, symb_atom.symbol, atom)
					self.watches.setdefault(solver_lit, []).append(watch)

		
		for (name, arity, atom) in domains:
			var_locs = atom.var_loc()
			for symb_atom in init.symbolic_atoms.by_signature(name, arity):
				solver_lit = init.solver_literal(symb_atom.literal)
				AtomMapping.add(atom.signature(), symb_atom.symbol, solver_lit)

				#VarLocToAtom.add_atom(symb_atom.symbol, self.get_vars_vals(symb_atom.symbol, var_locs))


		for lit in self.watches.keys():
			init.add_watch(lit)

		util.Count.add("watches", len(self.watches.keys()))

		print("Init is DONE")

	@util.Count("Propagate")
	def propagate(self, control, changes):
		with util.Timer("Propagation"):
			for c in changes:
				for cindex, symbol, atom in self.watches[c]:
					#print(f"\n\nstarting prop with atom {atom}")
					with util.Timer(f"ground-prop"):

						if self.ground(self.constraints[cindex].ground_orders[atom][0],
										self.constraints[cindex].ground_orders[atom][1],
										[c],
										self.get_vars_vals(symbol, atom.var_loc()),
										False,
										control) is None:
							return 
					#print("ending prop\n\n")

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



		contained, next_lit = order_pos[0]
		for atom in contained:
			if isinstance(atom, Comparison):
				#print(f"matching a comparsion {atom}")
				result = self.match_comparison(atom, current_assignment)
				#print(current_assignment)
				#print(atom, result)
				if result == False:
					return 1


			if isinstance(atom, Literal):
				#print("match contained ", atom, current_assignment)
				lit = self.match_contained_literal(atom, current_assignment)
				#print("lit result:", lit)

				new_is_unit = self.test_lit_truth_val(lit, is_unit, control)
				if new_is_unit is None:
					#print(" new is unit none")
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
					#print("all matches foundcont")
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
		#print("matches all for ", next_lit)
		return 1

	@util.Timer("match-cont-lit")
	def match_contained_literal(self, literal, assignment):
		#print(literal.eval(assignment), AtomMapping.atom_2_lit[literal.signature()])
		#print(type(literal.eval(assignment)))
		return AtomMapping.get_lit(literal.signature(), literal.eval(assignment)) * literal.sign

	def ground_neg(self, order_neg, current_ng, current_assignment, is_unit, control):
		# if we are here we have to deal with the negative atoms

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
	@util.Timer("get-next-lits")
	def get_next_lits(self, next_atom, current_assignment, is_unit, control):
		#print("get lits")
		matches = self.match_pos_atom(next_atom, current_assignment)
		#print("match count: ", len(matches))
		#print(matches)
		if len(matches) == 0:
			yield None, 0, is_unit
			return

		for match in matches:
			# for every match
			# grab lit of match
			new_is_unit = is_unit
			lit = AtomMapping.get_lit(next_atom.signature(), match)

			new_is_unit = self.test_lit_truth_val(lit, is_unit, control)
			if new_is_unit is None:
				continue
			
			#print("yielding match", match, lit)
			yield match, lit, new_is_unit
	@util.Timer("test-truth-val")
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
	@Memoize
	def match_pos_atom(self, atom, assignment):
		atom_sets = []

		for var, val in assignment.items():
			if var.var not in atom.variables:
				continue
			
			atoms = VarLocToAtom.atoms_by_var_val(atom, atom.varinfo_for_var(var.var), val)
			#print(atoms)

			if atoms is None:
				# if there is no atoms for a particular variable then the conflict cant exist
				return set()

			atom_sets.append(atoms)

		# this part here handles when an atom has no variables in the assignment
		if len(atom_sets) == 0:
			util.Count.add("atom with zero coverage")
			print("no coverage???", atom, assignment)
			return AtomMapping.atom_2_lit[atom.signature()].keys()

		with util.Timer("intersection"):
			util.Count.add("intersections made")
			sec = set.intersection(*atom_sets)

		return sec

	@util.Timer("Time to match Comparison")
	def match_comparison(self, comparison, assignment):
		#print(comparison, comparison.eval(assignment), assignment)
		return comparison.eval(assignment)

	@util.Timer("Time to Check")
	def check(self, control):
		for constraint in self.constraints:
			first_atom = constraint.body_parts[BodyType.pos_atom][0]
			order = constraint.ground_orders[first_atom]

			for ground_atom in AtomMapping.atom_2_lit[first_atom.signature()].keys():
				vars_val = self.get_vars_vals(ground_atom, first_atom.var_loc())

				lit = AtomMapping.get_lit(first_atom.signature(), ground_atom) * first_atom.sign
				if control.assignment.is_false(lit):
					continue

				if self.ground(order[0], order[1], [lit], vars_val, False, control) is None:
					return None
