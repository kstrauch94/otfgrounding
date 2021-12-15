from clingo.symbol import SymbolType
from clingo import Number

class Function:

	def __init__(self, name, args):
		self.name = name
		self.args = args
		self.arity = len(args)

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

	def match(self, term, assignment, bound_vars):
		# see if the atom matches the grounded atom, if a var is
		# not present in the assignment, it extends the assignment with
		# the value the of the grounded atom
		# when extending the assignment, it also adds the var to
		# bound_vars so that later on you have the information on which
		# vars were bounded by this match call and UNDO the extensions

		if term.type != SymbolType.Function:
			return False

		if self.arity != len(term.arguments):
			return False

		if self.name != term.name:
			return False

		for a, b in zip(self.args, term.arguments):
			if not a.match(b, assignment, bound_vars):
				return False

		return True

	def eval(self, assignment):
		arg_str = []
		for arg in self.args:
			arg_str.append(str(arg.eval(assignment)))

		return f"{self.name}({','.join(arg_str)})"


class Literal(Function):

	def __init__(self, function, sign) -> None:
		super().__init__(function.name, function.args)
		self.sign = sign

		self.atom_type = None

		self.is_fact()

	def signature(self):
		return self.name, self.arity

	def is_fact(self):
		self.is_fact = False
		if self.name.startswith("isfact_"):
			self.is_fact = True
			self.name = self.name.replace("isfact_", "")


	def assign_atom_type(self, atom_type):
		self.atom_type = atom_type

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

	def eval(self, assignment):
		return assignment[self.name]

	def match(self, term, assignment, bound_vars):
		if self.name in assignment:
			return term == assignment[self.name]
		assignment[self.name] = term
		bound_vars.append(self.name)
		return True

class SymbTerm:

	def __init__(self, symbterm):
		"""if hasattr(symbterm, "number"):
			self.symbterm = symbterm.number
		elif hasattr(symbterm, "string"):
			self.symbterm = symbterm.string
		else:
			self.symbterm = str(symbterm)"""

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

	def match(self, term):
		return term == self.symbterm

	def eval(self, vars_val):
		return self.symbterm

	def match(self, term, assignment, bound_vars):
		return self.symbterm == term

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

	def eval(self, assignment):
		# both sides have to be integers!!
		left = self.left.eval(assignment)
		right = self.right.eval(assignment)

		if self.op == "-":
			# check types!
			return left.number - right.number

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

	def eval(self, assignment):
		# term has to be a var or term integers!!
		val = self.arg.eval(assignment).number
		if self.op == "-":
			return Number(-val)

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

	def eval(self, assignment):
		left = self.left.eval(assignment)
		right = self.right.eval(assignment)

		if type(left) != type(right):
			raise TypeError(f"Types dont coincide for left {left} {type(left)} and right {right} {type(right)} {type(self.right)}")

		if self.op == "=":
			return left == right
		elif self.op == "<":
			return left < right
		elif self.op == ">":
			return left > right

		raise TypeError("op not known/implemented yet!")
