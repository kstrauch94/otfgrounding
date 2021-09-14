import argparse

from clingo import parse_term
from clingo.ast import Variable, parse_string
from clingox.ast import ast_to_dict

from collections import namedtuple

TYPE = {"ATOM": "atom", "DOM_COMPARISON": "dom_comparison"}


class Function:

	def __init__(self, name, args):
		self.name = name
		self.args = args

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
		return str(self.var)

	@property
	def vars(self):
		return [str(self)]

class Term:

	def __init__(self, term):
		self.term = term

	def __str__(self):
		return str(self.term)

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

def inspect_constraint(ast):

	dict_ast = ast_to_dict(ast)

	body_parts = []

	if dict_ast["ast_type"] == "Rule":
		for body in dict_ast["body"]:
			#print("BODDD", body)
			if body["atom"]["ast_type"] == "Comparison":
				# then its a comparison literal
				args = inspect_comparison(body)

				body_parts.append((TYPE["DOM_COMPARISON"], args))

			elif body["atom"]["ast_type"] == "SymbolicAtom":
				
				atom = inspect_ast(body["atom"]["symbol"])
				
				body_parts.append((TYPE["ATOM"], atom))

				print("the atom", atom)
				print("the vars", atom.vars)

	#import pprint
	#pp = pprint.PrettyPrinter()

	#for bp in body_parts:
	#	pp.pprint(bp)


def inspect_ast(dict_ast):
	if dict_ast["ast_type"] == "Variable":
		return Variable(dict_ast["name"])
	
	elif dict_ast["ast_type"] == "BinaryOperation":
		return BinaryOp(*inspect_binary_op(dict_ast))

	elif dict_ast["ast_type"] == "SymbolicTerm":
		#this is a string even if it is a "number"
		return Term(dict_ast["symbol"])

	elif dict_ast["ast_type"] == "Function":
		name = dict_ast["name"]
		args = []
		for arg in dict_ast["arguments"]:
			args.append(inspect_ast(arg))
		
		return Function(name, args)

	print(dict_ast)
	print("ERROR on the inspect_ast function!!")
	raise


bin_op = {4: "-"}
def inspect_binary_op(dict_ast):
	operation = []
	operator = dict_ast["operator_type"]
	operator = bin_op[operator]

	left = inspect_ast(dict_ast["left"])
	right = inspect_ast(dict_ast["right"])

	return left, operator, right

comp_op = {5: "="}
def inspect_comparison(dict_ast):
	left = inspect_ast(dict_ast["atom"]["left"])
	right = inspect_ast(dict_ast["atom"]["right"])

	operator = dict_ast["atom"]["comparison"]
	operator = comp_op[operator]

	return left, operator, right


def create_propagator_file(constraint):
	
	parse_string(constraint, inspect_constraint)


def compile():
	parser = argparse.ArgumentParser()

	parser.add_argument("constraints", help="File where the constraints are located.")

	args = parser.parse_args()
	
	with open(args.constraints, "r") as _f:
		for line in _f.readlines():
			create_propagator_file(line)
			

if __name__ == "__main__":
	compile()