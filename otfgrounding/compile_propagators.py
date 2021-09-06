import argparse

parser = argparse.ArgumentParser()

parser.add_argument("constraint-file", help="File where the constraints are located.")

args = parser.parse_args()

header = """
from collections import namedtuple

Class ATOM_VALS:
    
    true = "true"
    false = "False"
    unassigned = "None"
    not_grounded = "not_grounded"

"""

propapgator_init = """

class Propagator:

    def __init__(self):
        self.var_assignments = {assignment}
"""

propagator_init_func = """
    @util.Timer("Prop_init")
	def init(self, init):

        lits = set()

		for atom in {atom_list}:
			name, arity = atom
			for symb in init.symbolic_atoms.by_signature(name, arity):
				lit = init.solver_literal(symb.literal)
				AtomMap.add(symb.symbol, lit)
				lits.add(lit)
			
		for lit in lits:
			init.add_watch(lit)
"""

propagator_prop_func = """
    @util.Count("Propagation")
	@util.Timer("Propagation")
	def propagate(self, control, changes):
		for lit in changes:
			for atom in AtomMap.lit_2_atom[lit]:
				self.prop(control, atom, lit)


    def prop(self, control, atom, lit)

        ng = [lit]
        found_unassigned = False
        assignments = self.var_assignments.copy()

        name, arity, args = atom

        {if_blocks}
"""

propagator_if_outer_block = """
        if (name, arity) == ({name}, {arity}):
            
            {inner_blocks}

"""

propagator_if_inner_block = """
            for {atom} in {candidates}:
                res = self.test_candidate(atom, assignments)
                if res == ATOMVALS.false:
                    continue

                elif res == ATOMVALS.unassigned:
                    if found_unassigned == True:
                        continue

                    found_unassigned = True
                    lit = AtomMap.grab_lit({atom})
                    ng.append(lit)

                
                elif res == ATOMVALS.True:
                    lit = AtomMap.grab_lit({atom})
                    ng.append(lit)

"""

propagator_if_end_block = """

"""

if __name__ == "__main__":
    compile()