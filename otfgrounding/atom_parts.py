
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

	@property
	def vars(self):
		v = []
		for arg in self.args:
			v += arg.vars

		return v

	def substitute(self, subs):
		# do a function like this on everything!
		...

class Variable:

	def __init__(self, var):
		self.var = var

	def __str__(self):
		return f"{{{self.var}}}"

	@property
	def vars(self):
		return [str(self.var)]

class SymbTerm:

	def __init__(self, symbterm):
		self.symbterm = symbterm

	def __str__(self):
		return str(self.symbterm)

	@property
	def vars(self):
		return []

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
