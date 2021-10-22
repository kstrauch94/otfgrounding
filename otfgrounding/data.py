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

		self.type_count = 0

	def add(self, name, arity):

		if (name, arity) not in self.atom_to_type:
			self.atom_to_type[name, arity] = (name, arity)#self.type_count

			self.type_count += 1

	def get_type(self, name, arity):
		return self.atom_to_type[name, arity]

class VarToAtom:

	def __init__(self):
		self.vars_to_atom = {}


	def add_atom(self, atom_type, atom, vars_vals):

		for v in vars_vals:
			if v not in self.vars_to_atom:
				self.vars_to_atom[v] = {}

			if (atom_type, vars_vals[v]) not in self.vars_to_atom[v]:
				self.vars_to_atom[v][atom_type, vars_vals[v]] = set()

			self.vars_to_atom[v][atom_type, vars_vals[v]].add(atom)

	def atoms_by_var(self, atom_type, var, val):
		return self.vars_to_atom[var][atom_type, val]


class AtomMapping:

	lit_2_atom = {}

	atom_2_lit = {}


	@classmethod
	def add(cls, symbol, lit):
		#print(symbol)
		symb_str = str(symbol)

		if lit not in cls.lit_2_atom:
			cls.lit_2_atom[lit] = []

		cls.lit_2_atom[lit].append(symb_str)

		cls.atom_2_lit[symb_str] = lit

	@classmethod
	def get_lit(cls, symb_str):
		return cls.atom_2_lit[symb_str]

	@classmethod
	def get_atoms(cls, lit):
		return cls.lit_2_atom[lit]

class AtomMap:

	lit_2_atom = {}

	atom_2_lit = {}


	@classmethod
	def add(cls, symbol, lit):
		#print(symbol)
		name =  symbol.name
		args = [str(a) for a in symbol.arguments]
		arity = len(args)

		if lit not in cls.lit_2_atom:
			cls.lit_2_atom[lit] = []
		cls.lit_2_atom[lit].append(g_atom(name, arity, args))

		if not cls.check(name, arity):
			cls.atom_2_lit[name, arity] = {}

		last = cls.atom_2_lit[name, arity]
		for i in range(0, arity):

			str_arg = str(args[i])

			if i == arity-1:
				last[str_arg] = lit

			else:
				if str_arg not in last:
					last[str_arg] = {}

			last = last[str_arg]

	@classmethod
	def add_by_var(cls, symbol, lit, vars):
		name =  symbol.name
		args = [str(a) for a in symbol.arguments]
		arity = len(args)



	@classmethod
	def check(cls, name, arity):
		return (name, arity) in cls.atom_2_lit
