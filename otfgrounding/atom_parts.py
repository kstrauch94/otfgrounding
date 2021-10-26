

class Function:

	def __init__(self, name, args):
		self.name = name
		self.args = args
		self.arity = len(args)

	def __str__(self):
		arg_str = []
		for arg in self.args:
			arg_str.append(str(arg))

		return f"{self.name}({','.join(arg_str)})"

	def __repr__(self):
		return str(self)

	@property
	def vars(self):
		vars = []
		for arg in self.args:
			vars += arg.vars

		return vars

	def var_loc(self):
		vars = []
		for i, arg in enumerate(self.args):
			for v in arg.var_loc():
				v.add_pos(i)
				vars.append(v)

		return vars

	def substitute(self, subs):
		# do a function like this on everything!
		...


class Literal(Function):

	def __init__(self, function, sign) -> None:
		self.function = function
		self.sign = sign

		self.atom_type = None

	def assign_atom_type(self, atom_type):
		self.atom_type = atom_type

	@property
	def name(self):
		return self.function.name

	@property
	def args(self):
		return self.function.args

	@property	
	def arity(self):
		return self.function.arity

	def __str__(self):
		if self.sign == 1:
			return str(self.function)

		elif self.sign == -1:
			return "not " + str(self.function)

	def __repr__(self):
		return str(self)

	@property
	def vars(self):
		return self.function.vars

	def var_loc(self):
		return self.function.var_loc()

	def substitute(self, subs):
		# do a function like this on everything!
		...

class Variable:

	def __init__(self, var):
		self.var = var

	def __str__(self):
		return f"{self.var}"

	@property
	def vars(self):
		return [str(self.var)]

	def var_loc(self):
		return [VarInfo(self.var)]

	def __repr__(self):
		return str(self)

class SymbTerm:

	def __init__(self, symbterm):
		self.symbterm = symbterm

	def __str__(self):
		return str(self.symbterm)

	@property
	def vars(self):
		return []

	def var_loc(self):
		return []

	def __repr__(self):
		return str(self)

class BinaryOp:

	def __init__(self, left, op, right):
		self.left = left
		self.op = op
		self.right = right

	def __str__(self):
		return str(self.left) + str(self.op) + str(self.right)

	@property
	def vars(self):
		return self.left.vars + self.right.vars

	def var_loc(self):
		return self.left.var_loc() + self.right.var_loc()

	def __repr__(self):
		return str(self)

class VarInfo:

	def __init__(self, var):
		self.var = var

		self.positions = []

	def add_pos(self, i):
		self.positions.insert(0,i)

	def __str__(self):
		return f"{self.var} -- {self.positions}"

	def __repr__(self):
		return str(self)

class Comparison:

	def __init__(self, left, op, right):
		self.left = left
		self.op = op
		self.right = right

	@property
	def vars(self):
		return self.left.vars + self.right.vars

	def __str__(self):
		return str(self.left) + str(self.op) + str(self.right)

	def __repr__(self):
		return str(self)
