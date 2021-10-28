

class Function:

	def __init__(self, name, args):
		self.name = name
		self.args = args
		self.arity = len(args)

		self.var_loc_cached = None

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
		if self.var_loc_cached is None:
			vars = []
			for i, arg in enumerate(self.args):
				for v in arg.var_loc():
					v.add_pos(i)
					vars.append(v)

			self.var_loc_cached = vars

		return self.var_loc_cached

	def eval(self, vars_val):
		arg_str = []
		for arg in self.args:
			arg_str.append(str(arg.eval))

		return f"{self.name}({','.join(arg_str)})"


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

	def eval(self, vars_val):
		val = vars_val[self.var]
		try:
			val = int(val)
			return val
		except ValueError:
			return val

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

	def eval(self, vars_val):
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

	def eval(self, vars_val):
		# both sides have to be integers!!
		left = int(self.left.eval(vars_val))
		right = int(self.right.eval(vars_val))

		if self.op == "-":
			# check types!
			return left - right

		raise TypeError("op not known/implemented yet!")

class UnaryOp:

	def __init__(self, op, arg):
		self.op = op
		self.arg = arg

	def __str__(self):
		return str(self.op) + str(self.arg)

	@property
	def vars(self):
		return self.arg.vars

	def var_loc(self):
		return self.arg.var_loc()

	def __repr__(self):
		return str(self)

	def eval(self, vars):
		# term has to be a var or term integers!!
		val = int(self.arg.eval(vars))
		if self.op == "-":
			return -val

		raise TypeError("op not known/implemented yet!")
	

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

	def eval(self, vars_val):
		left = self.left.eval(vars_val)
		right = self.right.eval(vars_val)

		if type(left) != type(right):
			raise TypeError(f"Types dont coincide for left {left} {type(left)} and right {right} {type(right)}")

		if self.op == "=":
			return left == right