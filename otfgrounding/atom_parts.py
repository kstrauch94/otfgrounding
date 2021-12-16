

class Function:

	def __init__(self, name, args):
		self.name = name
		self.args = args
		self.arity = len(args)

		self.var_loc_cached = None

		self.vars_cached = None

	def __str__(self):
		arg_str = []
		for arg in self.args:
			arg_str.append(str(arg))

		return f"{self.name}({','.join(arg_str)})"

	def __repr__(self):
		return str(self)

	@property
	def variables(self):
		if self.vars_cached is None:
			vars = []
			for arg in self.args:
				vars += arg.variables
			self.vars_cached = vars

		return self.vars_cached

	def var_loc(self):
		if self.var_loc_cached is None:
			vars = []
			for i, arg in enumerate(self.args):
				for v in arg.var_loc():
					v.add_pos(i)
					vars.append(v)

			self.var_loc_cached = vars

		return self.var_loc_cached

	def varinfo_for_var(self, var):
		if self.var_loc_cached is None:
			self.var_loc()

		for varinfo in self.var_loc_cached:
			if varinfo.var == var:
				return varinfo

	def eval(self, vars_val):
		arg_str = []
		for arg in self.args:
			arg_str.append(str(arg.eval(vars_val)))

		return f"{self.name}({','.join(arg_str)})"


class Literal(Function):

	def __init__(self, function, sign) -> None:
		self.function = function
		self.sign = sign

		self.atom_type = None

		self.var_loc_cached = None

		self.is_fact()

	def is_fact(self):
		self.is_fact = False
		if self.function.name.startswith("isfact_"):
			self.is_fact = True
			self.function.name = self.function.name.replace("isfact_", "")


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
	def variables(self):
		return self.function.variables

	def var_loc(self):
		if self.var_loc_cached is None:
			self.var_loc_cached = self.function.var_loc()

			for varinfo in self.var_loc_cached:
				varinfo.positions = tuple(varinfo.positions)

		return self.var_loc_cached

	def eval(self, vars_val):
		return self.function.eval(vars_val)

class Variable:

	def __init__(self, var):
		self.name = var

	def __str__(self):
		return f"{self.name}"

	@property
	def variables(self):
		return [str(self.name)]

	def var_loc(self):
		return [VarInfo(self.name)]

	def __repr__(self):
		return str(self)

	def eval(self, vars_val):
		for var in vars_val:
			if var.var == self.name:
				val = vars_val[var]
		try:
			val = int(val)
			return val
		except ValueError:
			return val

class SymbTerm:

	def __init__(self, symbterm):
		if hasattr(symbterm, "number"):
			self.symbterm = symbterm.number
		elif hasattr(symbterm, "string"):
			self.symbterm = symbterm.string
		else:
			self.symbterm = str(symbterm)

	def __str__(self):
		return str(self.symbterm)

	@property
	def variables(self):
		return []

	def var_loc(self):
		return []

	def __repr__(self):
		return str(self)

	def eval(self, vars_val):
		return self.symbterm

class BinaryOp:

	def __init__(self, left, op, right):
		self.left = left
		self.op = op
		self.right = right

	def __str__(self):
		return str(self.left) + str(self.op) + str(self.right)

	@property
	def variables(self):
		return self.left.variables + self.right.variables

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
	def variables(self):
		return self.arg.variables

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


class Comparison:

	def __init__(self, left, op, right):
		self.left = left
		self.op = op
		self.right = right

	@property
	def variables(self):
		return self.left.variables + self.right.variables

	def __str__(self):
		return str(self.left) + str(self.op) + str(self.right)

	def __repr__(self):
		return str(self)

	def eval(self, vars_val):
		left = self.left.eval(vars_val)
		right = self.right.eval(vars_val)

		if type(left) != type(right):
			raise TypeError(f"Types dont coincide for left {left} {type(left)} and right {right} {type(right)} {type(self.right)}")

		if self.op == "=":
			return left == right
		elif self.op == "<":
			return left < right
		elif self.op == ">":
			return left > right

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
