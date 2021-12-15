from enum import Enum
from collections import namedtuple

g_atom = namedtuple("g_atom", ["name", "arity", "args"])

class BodyType(Enum):
	pos_atom = 1
	neg_atom = -1
	dom_comparison = 5


class AtomTypes:

	def __init__(self):
		self.atom_to_type = {}
		self.type_to_atom = {}

		self.type_count = 0

	def add(self, atom):

		name, arity = atom.name, atom.arity

		if (name, arity) not in self.atom_to_type:
			self.atom_to_type[name, arity] = self.type_count

			self.type_to_atom[self.type_count] = [atom]

			self.type_count += 1

			return self.type_count - 1

		else:
			atom_type = self.atom_to_type[name, arity]
			self.type_to_atom[atom_type].append(atom)

			return atom_type

	def get_type(self, name, arity):
		return self.atom_to_type[name, arity]

	def get_atom(self, atom_type):
		return self.type_to_atom[atom_type]

	def contains_atom(self, name, arity):
		return (name, arity) in self.atom_to_type


class VarLocToAtom:

	var_to_atom = {}

	@classmethod
	def add_atom(cls, atom_type, atom, vars_vals):

		for var, value in vars_vals.items():
			#if var.positions not in cls.var_to_atom:
			#	cls.var_to_atom[var.positions] = {}

			if (var.positions, atom_type, value) not in cls.var_to_atom:
				cls.var_to_atom[var.positions, atom_type, value] = set()

			cls.var_to_atom[var.positions, atom_type, value].add(atom)

	@classmethod
	def atoms_by_var_val(cls, atom_type, var, val):
		if (var.positions, atom_type, val) not in cls.var_to_atom:
			#print("?? ", cls.var_to_atom[var.positions])
			return None

		return cls.var_to_atom[var.positions, atom_type, val]

	@classmethod
	def atoms_by_var(cls, atom_type, var):
		atoms = set()

		for positions, other_atom_type, val in cls.var_to_atom:
			if atom_type != other_atom_type:
				continue

			atoms.update(cls.var_to_atom[positions, atom_type, val])

		return atoms



class AtomMapping:

	lit_2_atom = {}

	atom_2_lit = {}


	str_atom_2_lit = {}


	@classmethod
	def add(cls, symbol, sign, lit):
		#print(symbol)

		if lit not in cls.lit_2_atom:
			cls.lit_2_atom[lit] = []

		cls.lit_2_atom[lit].append((symbol, sign))

		cls.str_atom_2_lit[(str(symbol), sign)] = lit
		cls.atom_2_lit[symbol, sign] = lit


	@classmethod
	def get_lit(cls, symbol, sign):
		if (symbol, sign) not in cls.atom_2_lit:
			return -1
		return cls.atom_2_lit[symbol, sign]

	@classmethod
	def get_lit_from_str(cls, lit_str, sign):
		if (lit_str, sign) not in cls.str_atom_2_lit:
			return -1
		return cls.str_atom_2_lit[lit_str, sign]

	@classmethod
	def get_atoms(cls, lit):

		return cls.lit_2_atom[lit]
