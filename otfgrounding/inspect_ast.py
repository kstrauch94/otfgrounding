from otfgrounding.atom_parts import *
from otfgrounding.data import BodyType

from clingo.ast import Sign
from clingo.ast import ASTType


class ConstraintInspector:

	bin_op = {4: "-"}
	comp_op = {5: "="}

	def __init__(self):
		self.body_parts = {BodyType.dom_comparison: [],
							BodyType.pos_atom: [],
							BodyType.neg_atom: []}

	def inspect_constraint(self, ast):


		if ast.ast_type == ASTType.Rule:
			for body in ast.body:
				if body.ast_type == ASTType.Literal:
					if body.atom.ast_type == ASTType.Comparison:
						# then its a comparison literal
						args = self.inspect_comparison(body)

						self.body_parts[BodyType.dom_comparison].append(Comparison(*args))

					elif body.atom.ast_type == ASTType.SymbolicAtom:

						atom = self.inspect_ast(body.atom.symbol)

						if body.sign == Sign.NoSign:
							self.body_parts[BodyType.pos_atom].append(Literal(atom, 1))
						elif body.sign == Sign.Negation:
							self.body_parts[BodyType.neg_atom].append(Literal(atom, -1))
						else:
							print("ERROR???", body.sign)

						print("the atom", atom)
						print("the vars", atom.vars)

		#import pprint
		#pp = pprint.PrettyPrinter()

		#for bp in body_parts:
		#	pp.pprint(bp)


	def inspect_ast(self, ast):
		if ast.ast_type == ASTType.Variable:
			return Variable(ast.name)

		elif ast.ast_type == ASTType.BinaryOperation:
			return BinaryOp(*self.inspect_binary_op(ast))

		elif ast.ast_type == ASTType.SymbolicTerm:
			#this is a string even if it is a "number"
			return SymbTerm(ast.symbol)

		elif ast.ast_type == ASTType.Function:
			name = ast.name
			args = []
			for arg in ast.arguments:
				args.append(self.inspect_ast(arg))

			return Function(name, args)

		print(ast)
		print("ERROR on the inspect_ast function!!")
		raise



	def inspect_binary_op(self, ast):
		operation = []
		operator = ast.operator_type
		operator = ConstraintInspector.bin_op[operator]

		left = self.inspect_ast(ast.left)
		right = self.inspect_ast(ast.right)

		return left, operator, right


	def inspect_comparison(self, ast):
		left = self.inspect_ast(ast.atom.left)
		right = self.inspect_ast(ast.atom.right)

		operator = ast.atom.comparison
		operator = ConstraintInspector.comp_op[operator]

		return left, operator, right
