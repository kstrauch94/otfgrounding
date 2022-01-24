from email.mime import base
from clingo import Function as clingoFunction
from clingo import Number as clingoNumber

from typing import Dict, List, Any, OrderedDict, Set
from collections import defaultdict

import otfgrounding.util as util
from otfgrounding.data import AtomMapping
from otfgrounding.data import TemporalAtomMapping
from otfgrounding.data import TemporalAtoms
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

			atom_vars = atom.variables.copy()
			if atom.is_temporal:
				atom_vars.add("T")
			order = self.order_with_starter_and_containment(atom,
															[a for a in self.body_parts[BodyType.pos_atom] if a != atom],
															set(atom_vars.copy()))

			print("slotting comparisons and neg atoms:", self.body_parts[BodyType.dom_comparison], self.body_parts[BodyType.neg_atom])
			order = self.slot_atoms(order, self.body_parts[BodyType.dom_comparison] + self.body_parts[BodyType.neg_atom], atom_vars.copy())
			print(order)

			self.ground_orders[atom] = order

		print(self.ground_orders)


	def order_with_starter_and_containment(self, starter, rest, seen_vars):
		# returns a list of (atom, bool) pairs where the bool indicated
		# whether or not the variables in the atom are alrady contained in the 
		# assignment by that point
		if rest == []:
			return [(None, False)]

		contained = []
		for atom in rest:
			if set(atom.variables).issubset(seen_vars):
				contained.append(atom)

		new_rest = [a for a in rest if a not in contained]

		if new_rest == []:
			return [(contained_atom, True) for contained_atom in contained] + [(None, False)]

		#new_rest, best_atom = self.get_new_rest_counts(new_rest, seen_vars)
		new_rest, best_atom = self.new_rest_by_score(new_rest, seen_vars)

		seen_vars.update(best_atom.variables)

		return [(contained_atom, True) for contained_atom in contained] + [(best_atom, False)] + self.order_with_starter_and_containment(best_atom, new_rest, seen_vars)

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
		
	def slot_atoms(self, order, atoms_to_slot, starter_vars):
		print("using ", order, "to slot")
		if atoms_to_slot == []:
			return order

		avail_vars = set(starter_vars.copy())

		new_order = []

		my_atoms = atoms_to_slot.copy()

		to_remove = []
		for atom, contained in order:
			if contained:
				new_order.append((atom, contained))
				continue
			print("checking for slotting with ", avail_vars)
			
			for c in my_atoms:
				if set(c.variables).issubset(avail_vars):
					# can slot comparison for the avail vars BEFORE using
					# the next atom to ground
					new_order.append((c, True))
					print("slotted ", c)

					to_remove.append(c)
			my_atoms = [c for c in my_atoms if c not in to_remove]
			to_remove = []

			# Once we have appended all the comparison use the next atom
			# to ground to update the avail vars for the next run
			if atom is not None:
				print("updating ", avail_vars, "with ", atom.variables)
				avail_vars.update(atom.variables)
			else:
				print("atom is None", None)

			new_order.append((atom, contained))

			print("left atoms after slotting here", my_atoms)

		return new_order


class PropagatorAST:

	amt = 0

	def __init__(self, constraints):
		self.logger = logging.getLogger(self.__module__ + "." + self.__class__.__name__)

		self.constraints = constraints
		
		self.watches = {}

		self.temporal_watches = {}

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
				domains.add((atom.non_temporal_signature(), atom.is_temporal))
				# if atom is a fact still add it to the domains but do not add watches or anything like that

		# first loop over atoms
		# set all base atoms
		with util.Timer("signature set"):
			for (name, arity), temporal in domains:
				if not temporal:
					continue
				for symb_atom in init.symbolic_atoms.by_signature(name, arity):
					TemporalAtoms.add(symb_atom.symbol)
	

		to_watch = set()	
		for index, constraint in enumerate(self.constraints):
			for atom in constraint.all_atoms:
				if atom.is_fact:
					continue
				if atom.is_temporal:
					for symb_atom in init.symbolic_atoms.by_signature(*atom.non_temporal_signature()):
						solver_lit = init.solver_literal(symb_atom.literal) * atom.sign
						temp_symb = clingoFunction(atom.name, symb_atom.symbol.arguments[:-1])
						base_lit = TemporalAtoms.symbol_to_base_lit(atom.signature(), temp_symb)
						watch = (index, temp_symb, atom)
						self.temporal_watches.setdefault(base_lit*atom.sign, set()).add(watch)

						to_watch.add(solver_lit)

						timepoint = symb_atom.symbol.arguments[-1].number

						temporal_lit = TemporalAtoms.base_lit_to_temporal_lit(base_lit, timepoint, atom.sign)
						TemporalAtomMapping.add(temporal_lit, solver_lit)
				else:
					for symb_atom in init.symbolic_atoms.by_signature(*atom.non_temporal_signature()):
						solver_lit = init.solver_literal(symb_atom.literal) * atom.sign
						watch = (index, symb_atom.symbol, atom)
						self.watches.setdefault(solver_lit, []).append(watch)

						to_watch.add(solver_lit)

		with util.Timer("set mappings"):
			for (name, arity), temporal in domains:
				if temporal:
					continue
				for symb_atom in init.symbolic_atoms.by_signature(name, arity):
					solver_lit = init.solver_literal(symb_atom.literal)
					AtomMapping.add((name, arity), symb_atom.symbol, solver_lit)


		for lit in to_watch:
			init.add_watch(lit)

		util.Count.add("watches", len(to_watch))
		util.Count.add("normal wathces", len(self.watches.keys()))
		util.Count.add("temporal watches", len(self.temporal_watches.keys()))

		print("Init is DONE")

	@util.Count("Propagate")
	def propagate(self, control, changes):
		with util.Timer("Propagation"):
			for c in changes:

				# propagate normal watches
				if c in self.watches:

					for cindex, symbol, atom in self.watches[c]:
						util.Count.add("-----nground calls")
						#print(f"\n\nstarting prop with atom {atom}")
						with util.Timer(f"ground-prop-normal"):
							assignment = {}
							atom.match(symbol, assignment, [])
							if self.ground(self.constraints[cindex].ground_orders[atom],
											[c],
												assignment,
											False,
											control) is None:
								return 
						#print("ending prop\n\n")
				for t_lit in TemporalAtomMapping.get_t_lit(c):
					s_base_lit = TemporalAtoms.temporal_lit_to_s_base_lit(t_lit)
					if s_base_lit not in self.temporal_watches:
						continue
					timepoint = TemporalAtoms.temporal_lit_to_time(t_lit)

					for cindex, temp_symbol, atom in self.temporal_watches[s_base_lit]:
						util.Count.add("----ground calls")
						with util.Timer(f"ground-prop-temporal"):
							assignment = {"T": clingoNumber(atom.convert_to_assigned_time(timepoint))}
							atom.match(temp_symbol, assignment, [])
							if self.ground(self.constraints[cindex].ground_orders[atom],
											[c],
											assignment,
											False,
											control) is None:
								return 
						#print("ending prop\n\n")

	#@profile
	def ground(self, order, nogood, assignment, is_unit, control):

		next_lit, contained = order[0]	
		if next_lit is None:
			# we have reached the end and it is time to add the nogoog
			util.Count.add("Constraint added")
			if not control.add_nogood(nogood) or not control.propagate():
				#print("adding constraint", assignment)
				return None

		elif contained:
			if isinstance(next_lit, Comparison):
				#print(f"matching a comparsion {atom}")
				#print(assignment)
				#print(atom, result)

				# evaluate comparison -> should return true or false
				if next_lit.eval(assignment):
					if self.ground(order[1:], nogood, assignment, is_unit, control) is None:
						return None

			else:
				lit = self.match_contained_literal(next_lit, assignment)
				lit_val = control.assignment.value(lit)
				if lit_val == False:
					#print("lit contained false", next_lit, assignment, lit)
					return 1
					
				if not (lit_val is None and is_unit):
					# only the new lit can be unassigned
					nogood.append(lit)
					if self.ground(order[1:], nogood, assignment, is_unit or lit_val is None, control) is None:
						return None
					nogood.pop()

		else:
			# atom here has to be positive and not contained

			#print("next: ", next_lit)
			#print(assignment)
			for match in self.match_pos_atom(next_lit, assignment):
				util.Count.add("------match found")
				# print("match ", match)
				# getting here means lit is true or the first unassigned one
				bound = []
				if next_lit.is_temporal:
					with util.Timer("----temporal 1"):
						timepoint = next_lit.convert_to_normal_time(assignment["T"]).number
						lit = TemporalAtomMapping.get_lit(TemporalAtoms.symbol_to_temporal_lit(next_lit.signature(), match, timepoint, next_lit.sign))
				else:
					lit = AtomMapping.atom_2_lit[next_lit.signature()][match]
				# don't have to multiply lit by sign since it should always be positive atom

				lit_val = control.assignment.value(lit)
				if lit_val == False:
					continue
				if not (lit_val is None and is_unit):

					next_lit.match(match, assignment, bound)
					nogood.append(lit)

					if self.ground(order[1:], nogood, assignment, is_unit or lit_val is None, control) is None:
						return None
					
					nogood.pop()
					for var in bound:
						del assignment[var]

		#print("matches all for ", next_lit)
		return 1

	@util.Timer("match-cont-lit")
	def match_contained_literal(self, literal, assignment):
		#print(literal.eval(assignment), AtomMapping.atom_2_lit[literal.signature()])
		#print(type(literal.eval(assignment)))
		if literal.is_temporal:
			with util.Timer("----temporal cont"):
				eval_lit = literal.eval(assignment)
				timepoint = literal.convert_to_normal_time(assignment["T"]).number
				#AtomMapping.get_lit(literal.non_temporal_signature(), eval_lit.arguments.append(timepoint)) * literal.sign

				return TemporalAtomMapping.get_lit(TemporalAtoms.symbol_to_temporal_lit(literal.signature(), eval_lit, timepoint, literal.sign))

		else:
			return AtomMapping.get_lit(literal.signature(), literal.eval(assignment)) * literal.sign

	@util.Timer("Time to match pos atom")
	#@profile
	@Memoize
	def match_pos_atom(self, atom, assignment):
		atom_sets = []

		#for var in atom.variables.intersection(assignment.keys()):
		for var, val in assignment.items():
			if var not in atom.variables:
				continue
			
			for pos in atom.var_to_loc[var]:
				atoms = VarLocToAtom.atoms_by_var_val(atom, pos, val)
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
			if atom.is_temporal:
				new_sec = set()
				for temporal_atom in sec:
					temporal_lit = TemporalAtoms.symbol_to_temporal_lit(atom.signature(), temporal_atom, atom.convert_to_normal_time(assignment["T"]).number, atom.sign)
					if temporal_lit in TemporalAtomMapping.t_lit_2_lit:
						new_sec.add(temporal_atom)
				
				sec = new_sec
		return sec

	@util.Timer("Time to Check")
	@util.Count("checks")
	def check(self, control):
		#return
		for constraint in self.constraints:

			first_atom = list(constraint.ground_orders.keys())[0]
			order = constraint.ground_orders[first_atom]

			if first_atom.is_temporal:
				for ground_atom in TemporalAtoms.t_atom_2_t_lit[first_atom.signature()].keys():
					for timepoint in range(0,100):
						lit = TemporalAtomMapping.get_lit(TemporalAtoms.symbol_to_temporal_lit(first_atom.signature(), ground_atom, timepoint, first_atom.sign))
						util.Count.add("atoms to try")
						if control.assignment.is_false(lit):
							continue
						util.Count.add("atoms checked")
						assignment = {"T": clingoNumber(timepoint)}
						first_atom.match(ground_atom, assignment, [])

						if self.ground(order, [lit], assignment, False, control) is None:
							return None

			else:
				for ground_atom in AtomMapping.atom_2_lit[first_atom.signature()].keys():
					assignment = {}
					lit = AtomMapping.get_lit(first_atom.signature(), ground_atom) * first_atom.sign

					if control.assignment.is_false(lit):
							continue

					assignment = {}
					first_atom.match(ground_atom, assignment, [])
