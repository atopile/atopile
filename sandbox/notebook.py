# %%
import numpy as np
import scipy as sp
from scipy.optimize import fsolve, minimize
# from sympy import parse_expr, lambdify, Symbol

# %%

"""
eqns:

eq 1 : v_out = v_ref
eq 2 : v_out = v_in * (r_top / (r_bot + r_top))
eq 3 : i_q = v_in / (r_bot + r_bot)
"""

def eq1(v_out, v_ref):
    return v_out - v_ref

def eq2(v_out, v_in, r_top, r_bot):
    return v_out - v_in * (r_top / (r_bot + r_top))

def eq3(i_q, v_in, r_bot):
    return i_q - v_in / (r_bot + r_bot)

def dispatch_eqn(vals: np.ndarray) -> np.ndarray:
    v_out, v_ref, v_in, r_top, r_bot, i_q = vals
    return np.array([eq1(v_out, v_ref), eq2(v_out, v_in, r_top, r_bot), eq3(i_q, v_in, r_bot)])

# %%

from scipy.optimize import fsolve

fsolve(dispatch_eqn, [0, 0, 10, 1000, 1000, 1])
# %%
import numpy as np
from scipy.optimize import fsolve

# Circle parameters
x_c, y_c, r = 0, 0, 5  # Center and radius of the circle

# External point and desired distance
x_p, y_p, d = 7, 7, 5

# Constraint equations
def constraints(vars):
    x, y = vars
    return [
        (x - x_c)**2 + (y - y_c)**2 - r**2,  # Point on circle constraint
        np.sqrt((x - x_p)**2 + (y - y_p)**2) - d  # Distance to external point constraint
    ]

# Initial guess for (x, y)
initial_guess = [x_c, y_c]

# Solve the system of equations
solution = fsolve(constraints, initial_guess)
print(f"Solution point: {solution}")


# %%
x = Symbol('x')
y = Symbol('y')
_c = lambdify((x, y), parse_expr("(x - 1) ** 2 + 1 - y"))

def c(vars):
    x, y = vars
    return _c(x, y)

cons = ({'type': 'eq', 'fun': c})

def objective(vars):
    x, y = vars
    return y

# %%
initial_guess = [0, 0]
solution = minimize(objective, initial_guess, constraints=cons, method='SLSQP')
solution

# %%
from sympy import lambdify, symbols
v_out, v_in, r_top, r_bottom, i_q = symbols('v_out v_in r_top r_bottom i_q')
all_vars = [v_out, v_in, r_top, r_bottom, i_q]

def lambdify2(expr_str: str):
    expr = parse_expr(expr_str)
    lamdified = lambdify(all_vars, expr)
    def _func(vars):
        return lamdified(*vars)
    return _func


# %%
"""
Goal: Make an assertion statment like this check it's always true, given the ranges of the variables

assert v_in * r_bot.value / (r_top.value + r_bot.value) in v_out
"""

