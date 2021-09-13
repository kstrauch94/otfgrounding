import argparse

from clingo import parse_term
from clingo.ast import Variable, parse_string
from clingox.ast import ast_to_dict

from collections import namedtuple

TYPE = {"ATOM": "atom", "DOM_COMPARISON": "dom_comparison"}


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
				
				args = inspect_ast(body["atom"]["symbol"])
				
				body_parts.append((TYPE["ATOM"], args))

	import pprint
	pp = pprint.PrettyPrinter()

	for bp in body_parts:
		pp.pprint(bp)


def inspect_ast(dict_ast):
	if dict_ast["ast_type"] == "Variable":
		return dict_ast["name"]
	
	elif dict_ast["ast_type"] == "BinaryOperation":
		return inspect_binary_op(dict_ast)

	elif dict_ast["ast_type"] == "SymbolicTerm":
		#this is a string even if it is a "number"
		return dict_ast["symbol"]

	elif dict_ast["ast_type"] == "Function":
		name = dict_ast["name"]
		args = []
		for arg in dict_ast["arguments"]:
			args.append(inspect_ast(arg))
		
		return name, args

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