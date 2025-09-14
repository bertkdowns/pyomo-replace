from model import *
import pyomo.environ as pyo


m = pyo.ConcreteModel()
m.b1 = pyo.Block()
m.b1.x = pyo.Var()
m.b1.y = pyo.Var()
m.b1.c1 = pyo.Constraint(expr=m.b1.x + m.b1.y == 10)

register_block(m.b1, [m.b1.x])

replace_state_var(m.b1.x,m.b1.y)

pprint_replacements(m.b1)