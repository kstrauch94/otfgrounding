from enum import Enum
from collections import namedtuple
from typing import Sized
from otfgrounding import util
from clingo import SymbolType
from clingo import Function as clingoFunction

class BodyType(Enum):
	pos_atom = 1
	neg_atom = -1
	dom_comparison = 5

#@profile
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
	def atoms_by_var_val(cls, atom, var_position, value):
		
		if atom.is_temporal:
			mapping = TemporalAtoms.t_atom_2_t_lit
		else:
			mapping = AtomMapping.atom_2_lit

		if (var_position, atom.name, atom.arity, value) not in cls.var_to_atom:
			util.Count.add("Building the thing")
			for symbol in mapping[atom.name, atom.arity].keys():
				#if value_on_term_position(symbol, var.positions) == value:
					#cls.var_to_atom.setdefault((var.positions, atom.name, atom.arity, value), set()).add(symbol)
				val = value_on_term_position(symbol, var_position)
				cls.var_to_atom.setdefault((var_position, atom.name, atom.arity, val), set()).add(symbol)


			if (var_position, atom.name, atom.arity, value) not in cls.var_to_atom:
				util.Count.add("found no atoms")
				print(atom, var_position, value)
				cls.var_to_atom[var_position, atom.name, atom.arity, value] = None
			else:
				util.Count.add("found atoms!")

		return cls.var_to_atom[var_position, atom.name, atom.arity, value]

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


class TemporalAtoms:

	# temporal atom to temporal literal
	t_atom_2_t_lit = {}
	t_lit_2_t_atom = {}

	size = 0

	@classmethod
	def add(cls, symbol):
		
		temporal_symbol = clingoFunction(symbol.name, symbol.arguments[:-1])
		signature = (symbol.name, len(symbol.arguments) -1)
		if signature not in cls.t_atom_2_t_lit:
			cls.t_atom_2_t_lit[signature] = {}
			
		if temporal_symbol not in cls.t_atom_2_t_lit[signature]:
			cls.size += 1
			cls.t_atom_2_t_lit[signature][temporal_symbol] = cls.size
			cls.t_lit_2_t_atom[cls.size] = temporal_symbol

	@classmethod
	def get_base_lit(cls, signature, symbol):
		if signature not in cls.t_atom_2_t_lit:
			raise RuntimeError(f"temporal lit should exist: {symbol}")
		if symbol not in cls.t_atom_2_t_lit[signature]:
			raise RuntimeError(f"temporal lit should exist: {symbol}")

		return cls.atom_2_lit[signature][symbol]

	@classmethod
	def get_temporal_lit(cls, signature, symbol, timepoint):
		temp_lit = cls.get_temporal_lit(signature, symbol)

	@classmethod
	def convert_base_lit_to_temporal_lit(cls, base_lit, timepoint):
		return base_lit + (timepoint * cls.size)
	
	@classmethod
	def convert_to_base_lit(cls, temporal_lit):
		intermediate = temporal_lit % cls.size
		if intermediate == 0:
			intermediate = cls.size
		
		return intermediate

	@classmethod
	def convert_to_time(cls, temporal_lit):
		return (abs(temporal_lit) - 1) // cls.size

	@classmethod
	def add_time_to_base_lit(cls, base_lit, timepoint):
		return base_lit + (timepoint * cls.size)

	@classmethod
	def convert_temporal_lit_to_symbol(cls, temporal_lit):
		base_lit = cls.convert_to_base_lit(temporal_lit)
		timepoint = cls.convert_to_time(temporal_lit)

		temporal_symbol = cls.t_lit_2_t_atom[base_lit]

		return clingoFunction(temporal_symbol.name, temporal_symbol.arguments.append(clingo.Number(timepoint)))

class TemporalAtomMapping:

	lit_2_t_lit = {}

	@classmethod
	def add(cls, temporal_lit, solver_lit):
		cls.lit_2_t_lit.setdefault(solver_lit, []).append(temporal_lit)

	@classmethod
	def get_t_lit(cls, solver_lit):
		if solver_lit not in cls.lit_2_t_lit:
			return []
		return cls.lit_2_t_lit[solver_lit]