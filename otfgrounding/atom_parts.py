from clingo import Number
from clingo import Function as ClingoFunction

class Function:

	def __init__(self, name, args):
		self.name = name
		self.args = args
		self.arity = len(args)

		self.var_loc_cached = None

		self.var_to_loc = {}
		self.loc_to_var = {}

		self.vars_cached = None

	def score(self, vars):
		new_vars = len(set(self.variables).difference(vars)) # the new vars the atom would add
		old_vars = len(set(self.variables).intersection(vars)) + 1

		return 1000 * (new_vars / old_vars)

	def signature(self):
		return self.name, self.arity

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


			for var in self.var_loc_cached:
				var.positions = tuple(var.positions)
				self.var_to_loc[var.var] = var.positions
				self.loc_to_var[var.positions] = var.var

		return self.var_loc_cached

	def varinfo_for_var(self, var):
		if self.var_loc_cached is None:
			self.var_loc()

		for varinfo in self.var_loc_cached:
			if varinfo.var == var:
				return varinfo

	def eval(self, vars_val):
		#args = []
		#for arg in self.args:
		#	args.append(arg.eval(vars_val))

		return ClingoFunction(self.name, [arg.eval(vars_val) for arg in self.args])

	def var_on_pos(self, pos):
		return self.args[pos[0]].var_on_pos(pos[1:])

class Literal(Function):

	def __init__(self, function, sign) -> None:
		super().__init__(function.name, function.args)
		self.sign = sign

		self.is_fact()

	def is_fact(self):
		self.is_fact = False
		if self.name.startswith("isfact_"):
			self.is_fact = True
			self.name = self.name.replace("isfact_", "")

	def __str__(self):
		if self.sign == 1:
			return super().__str__()

		elif self.sign == -1:
			return "not " + super().__str__()

	def __repr__(self):
		return str(self)

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
				return vars_val[var]
			
		raise RuntimeError("Assignment does not have variable {} {}".format(vars_val, self.name))

	def var_on_pos(self, pos):
		if not pos:
			# if pos is empty tuple
			return self.name

class SymbTerm:

	def __init__(self, symbterm):
		self.symbterm = symbterm

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

	def var_on_pos(self, pos):
		raise RuntimeError("Looking for a var on a position that has a term")

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
		left = self.left.eval(vars_val)
		right = self.right.eval(vars_val)

		if self.op == "-":
			# check types!
			return Number(left.number - right.number)

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
			return Number(-val.number)

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
