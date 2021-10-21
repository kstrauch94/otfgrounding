import clingo

from otfgrounding.propagator.propagatorhandler import Handler

import otfgrounding.util as util

import textwrap as _textwrap

import logging
import sys

class Application:

	def __init__(self):
		self.version = "1.0"

		self.__handler = None

		self.__prop_init = clingo.Flag(False)

		self.cfile = None

	def __on_stats(self, step, accu):
		util.print_stats(step, accu)

	def register_options(self, options):
		"""
		Options for the temporal constraints
		"""
		group = "otf Options"

		options.add(group, "constraints", _textwrap.dedent("""Build propagator for the given constraints"""), self.__constraints)

	def __constraints(self, constraints):

		self.cfile = constraints

		return True

	def main(self, prg, files):
		with util.Timer("until solve"):
			for name in files:
				prg.load(name)

			self.__handler = Handler(self.cfile)

			with util.Timer("ground time"):
				prg.ground([("base", [])])
			print("clingo grounding done")

			self.__handler.register(prg)

		prg.solve(on_statistics=self.__on_stats)
		print("done!")

def setup_logger():
	root_logger = logging.getLogger()
	root_logger.setLevel(logging.INFO)

	logger_handler = logging.StreamHandler(stream=sys.stdout)

	formatter = logging.Formatter("%(levelname)s:%(name)s:\t%(message)s")

	logger_handler.setFormatter(formatter)

	root_logger.addHandler(logger_handler)


def main():
	setup_logger()
	sys.exit(int(clingo.clingo_main(Application(), sys.argv[1:])))

if __name__ == "__main__":
	main()
