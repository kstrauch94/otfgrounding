from enum import Enum
from collections import namedtuple
from otfgrounding import util
from clingo import SymbolType

class BodyType(Enum):
	pos_atom = 1
	neg_atom = -1
	dom_comparison = 5

@profile
def value_on_term_position(symbol, pos):
	new_s = symbol
	for p in pos:
		new_s = symbol.arguments[p]

	return new_s

class VarLocToAtom:

	var_to_atom = {}

	@classmethod
	def add_atom(cls, atom, vars_vals):
		# atom here is a Symbol object
		for var, value in vars_vals.items():

			cls.var_to_atom.setdefault((var.positions, atom.name, len(atom.arguments), value), set()).add(atom)

	@classmethod
	@util.Timer("build index")
	@util.Count("using the index")
	def atoms_by_var_val(cls, atom, var, value):
		if (var.positions, atom.name, atom.arity, value) not in cls.var_to_atom:
			util.Count.add("Building the thing")
			for symbol in AtomMapping.atom_2_lit[atom.name, atom.arity].keys():
				if value_on_term_position(symbol, var.positions) == value:
					cls.var_to_atom.setdefault((var.positions, atom.name, atom.arity, value), set()).add(symbol)


			if (var.positions, atom.name, atom.arity, value) not in cls.var_to_atom:
				util.Count.add("found no atoms")
				cls.var_to_atom[var.positions, atom.name, atom.arity, value] = None
			else:
				util.Count.add("found atoms!")

		return cls.var_to_atom[var.positions, atom.name, atom.arity, value]

	@classmethod
	def atoms_by_var(cls, atom, var):
		atoms = set()

		for positions, other_atom_name, other_atom_arity, val in cls.var_to_atom:
			if (atom.name, atom.arity) != (other_atom_name, other_atom_arity):
				continue

			atoms.update(cls.var_to_atom[positions, other_atom_name, other_atom_arity, val])

		return atoms



class AtomMapping:

	atom_2_lit = {}

	@classmethod
	def add(cls, signature, symbol, lit):

		cls.atom_2_lit.setdefault(signature, {})[symbol] = lit

	@classmethod
	def get_lit(cls, signature, symbol):
		if signature not in cls.atom_2_lit:
			return -1
		if symbol not in cls.atom_2_lit[signature]:
			return -1
		return cls.atom_2_lit[signature][symbol]
