import argparse

from clingo.ast import parse_string

from otfgrounding.inspect_ast import ConstraintInspector

def create_propagator_file(constraint):

	c_inspector = ConstraintInspector()

	parse_string(constraint, c_inspector.inspect_constraint)


def compile():
	parser = argparse.ArgumentParser()

	parser.add_argument("constraints", help="File where the constraints are located.")

	args = parser.parse_args()

	with open(args.constraints, "r") as _f:
		for line in _f.readlines():
			create_propagator_file(line)


if __name__ == "__main__":
	compile()
