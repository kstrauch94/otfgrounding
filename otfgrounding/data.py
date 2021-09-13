from collections import namedtuple

g_atom = namedtuple("g_atom", ["name", "arity", "args"])

class AtomMap:
	
	lit_2_atom = {}

	atom_2_lit = {}

	def __init__(self):
		...

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
	def check(cls, name, arity):
		return (name, arity) in cls.atom_2_lit
