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

	#@profile
	def atoms_by_var_val(self, atom_type, var, val):
		if (atom_type, val) not in self.vars_to_atom[var]:
			return None

		return self.vars_to_atom[var][atom_type, val]


	def atoms_by_var(self, atom_type, var):
		atoms = set()

		for other_atom_type, val in self.vars_to_atom[var]:
			if atom_type != other_atom_type:
				continue

			atoms.update(self.vars_to_atom[var][atom_type, val])

		return atoms

class AtomMapping:

	lit_2_atom = {}

	atom_2_lit = {}


	@classmethod
	def add(cls, symbol, sign, lit):
		#print(symbol)

		if lit not in cls.lit_2_atom:
			cls.lit_2_atom[lit] = []

		cls.lit_2_atom[lit].append((symbol, sign))

		cls.atom_2_lit[symbol, sign] = lit

	@classmethod
	def get_lit(cls, symbol, sign):
		return cls.atom_2_lit[symbol, sign]

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
