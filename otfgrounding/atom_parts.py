from clingo import Number
from clingo import Function as ClingoFunction
from clingo import SymbolType

class Function:

	def __init__(self, name, args):
		self.name = name
		self.args = args

		self.var_loc_cached = None

		self.var_to_loc = {}
		self.loc_to_var = {}

		self.vars_cached = None

		self.var_loc()

	def score(self, vars):
		new_vars = len(set(self.variables).difference(vars)) # the new vars the atom would add
		old_vars = len(set(self.variables).intersection(vars)) + 1

		return 1000 * (new_vars / old_vars)

	@property
	def arity(self):
		return len(self.args)

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
			vars = set()
			for arg in self.args:
				vars.update(arg.variables)
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


			for var_info in self.var_loc_cached:
				var_info.positions = tuple(var_info.positions)
				self.var_to_loc.setdefault(var_info.var, []).append(var_info.positions)
				self.loc_to_var[var_info.positions] = var_info.var

		return self.var_loc_cached

	def varinfo_for_var(self, var):
		if self.var_loc_cached is None:
			self.var_loc()

		for varinfo in self.var_loc_cached:
			if varinfo.var == var:
				return varinfo

	def eval(self, assignment):
		#args = []
		#for arg in self.args:
		#	args.append(arg.eval(vars_val))

		return ClingoFunction(self.name, [arg.eval(assignment) for arg in self.args])

	def var_on_pos(self, pos):
		return self.args[pos[0]].var_on_pos(pos[1:])

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

class Literal(Function):

	def __init__(self, function, sign) -> None:
		super().__init__(function.name, function.args)
		self.sign = sign

		self.is_fact = None
		self.is_temporal = None

		self.check_fact()
		self.check_temporal()

	def check_fact(self):
		self.is_fact = False
		if self.name.startswith("isfact_"):
			self.is_fact = True
			self.name = self.name.replace("isfact_", "")

	def check_temporal(self):
		self.is_temporal = False
		if self.name.startswith("temporal_"):
			self.is_temporal = True
			self.name = self.name.replace("temporal_", "")

			self.time = self.args[-1]
			self.args = self.args[:-1]

			self.assigned_time_binary_op = self.time.copy()

			if isinstance(self.assigned_time_binary_op, BinaryOp):
				if self.time.op == "-":
						inverse = "+"
				elif self.time.op == "+":
					inverse = "-"

				self.assigned_time_binary_op.op = inverse

	def non_temporal_signature(self):
		return self.name, self.arity + 1

	def convert_to_assigned_time(self, timepoint):
		# use this function to convert the time point given by a literal to the assigned time

		return self.assigned_time_binary_op.eval({"T": timepoint})

	def convert_to_normal_time(self, assigned_time):
		# given an assigned time, return the regular time
		return self.time.eval({"T": assigned_time})

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
		return set([self.name])

	def var_loc(self):
		return [VarInfo(self.name)]

	def __repr__(self):
		return str(self)

	def eval(self, assignment):
		if self.name in assignment:
			return assignment[self.name]
			
		raise RuntimeError("Assignment does not have variable {} {}".format(assignment, self.name))

	def var_on_pos(self, pos):
		if not pos:
			# if pos is empty tuple
			return self.name

	def match(self, term, assignment, bound_vars):
		if self.name in assignment:
			return term == assignment[self.name]
		assignment[self.name] = term
		bound_vars.append(self.name)
		return True


class SymbTerm:

	def __init__(self, symbterm):
		self.symbterm = symbterm

	def __str__(self):
		return str(self.symbterm)

	@property
	def variables(self):
		return set()

	def var_loc(self):
		return []

	def __repr__(self):
		return str(self)

	def eval(self, vars_val):
		return self.symbterm

	def var_on_pos(self, pos):
		raise RuntimeError("Looking for a var on a position that has a term")

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
		return self.left.variables.union(self.right.variables)

	def var_loc(self):
		return self.left.var_loc() + self.right.var_loc()

	def __repr__(self):
		return str(self)

	def eval(self, vars_val):
		# both sides have to be integers!!
		left = self.left.eval(vars_val)
		right = self.right.eval(vars_val)

		if self.op == "-":
			return Number(left.number - right.number)
		
		elif self.op == "+":
			return Number(left.number + right.number)

		elif self.op == "*":
			return Number(left.number * right.number)

		elif self.op == "/":
			return Number(left.number / right.number)

		raise TypeError(f"op {self.op} not known/implemented yet!")

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
		val = self.arg.eval(assignment)
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
		return self.left.variables.union(self.right.variables)

	def __str__(self):
		return str(self.left) + str(self.op) + str(self.right)

	def __repr__(self):
		return str(self)

	def eval(self, assignment):
		left = self.left.eval(assignment)
		right = self.right.eval(assignment)

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
