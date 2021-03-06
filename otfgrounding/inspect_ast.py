from otfgrounding.atom_parts import *
from otfgrounding.data import BodyType

from clingo.ast import Sign
from clingo.ast import ASTType


class ConstraintInspector:
	un_op = {0: "-"}

	bin_op = {4: "-",
			  3: "+",
			  5: "*",
			  6: "/"}

	comp_op = {5: "=",
			   1: "<",
			   0: ">"}

	def __init__(self, prg):
		self.body_parts = {BodyType.dom_comparison: [],
							BodyType.pos_atom: [],
							BodyType.neg_atom: []}

		self.prg = prg

	def inspect_constraint(self, ast):
		print("Inspection!")

		if ast.ast_type == ASTType.Rule:
			for body in ast.body:
				if body.ast_type == ASTType.Literal:
					if body.atom.ast_type == ASTType.Comparison:
						# then its a comparison literal
						args = self.inspect_comparison(body)

						comp = Comparison(*args)
						self.body_parts[BodyType.dom_comparison].append(comp)

						print("the comp", comp)

					elif body.atom.ast_type == ASTType.SymbolicAtom:

						atom = self.inspect_ast(body.atom.symbol)

						if body.sign == Sign.NoSign:
							lit = Literal(atom, 1)
							self.body_parts[BodyType.pos_atom].append(lit)
						elif body.sign == Sign.Negation:
							lit = Literal(atom,-1)
							self.body_parts[BodyType.neg_atom].append(lit)
						else:
							print("ERROR???", body.sign)

						print("the atom", lit)
						print("the vars", lit.variables)

		#import pprint
		#pp = pprint.PrettyPrinter()

		#for bp in body_parts:
		#	pp.pprint(bp)


	def inspect_ast(self, ast):
		if ast.ast_type == ASTType.Variable:
			return Variable(ast.name)

		elif ast.ast_type == ASTType.BinaryOperation:
			return BinaryOp(*self.inspect_binary_op(ast))

		elif ast.ast_type == ASTType.UnaryOperation:
			return UnaryOp(*self.inspect_unary_op(ast))

		elif ast.ast_type == ASTType.SymbolicTerm:
			#this is a string even if it is a "number"
			const = self.prg.get_const(str(ast.symbol))
			if const is not None:
				return SymbTerm(const)
			
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
		operator = ast.operator_type
		operator = ConstraintInspector.bin_op[operator]

		left = self.inspect_ast(ast.left)
		right = self.inspect_ast(ast.right)

		return left, operator, right

	def inspect_unary_op(self, ast):
		operator = ast.operator_type
		operator = ConstraintInspector.un_op[operator]

		arg = self.inspect_ast(ast.argument)

		return operator, arg


	def inspect_comparison(self, ast):
		left = self.inspect_ast(ast.atom.left)
		right = self.inspect_ast(ast.atom.right)

		operator = ast.atom.comparison
		operator = ConstraintInspector.comp_op[operator]

		return left, operator, right
