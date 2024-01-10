#%%

import sympy
import math
import numpy as np
import matplotlib.pyplot as plt

# ==========================
# GLOBAL VARIABLES
# ==========================

k_cost_resistor = 1
k_cost_capacitor = 2
k_cost_inductor = 3


def print_outline(symbol_1, value_1, tolerance_1, symbol_2, value_2, tolerance_2, equation, symbol_output, value_output, tolerance_output):
    print("allowed values for", symbol_output, "are between", value_output * (1 - tolerance_output), "and", value_output * (1 + tolerance_output))
    options = [[1,1], [-1,-1], [-1, 1], [1,-1]]
    outline_values = []
    for option in options:
        subbed_equation = equation.subs({symbol_1: (value_1 + value_1 * tolerance_1 * option[0]), symbol_2: (value_2 + value_2 * tolerance_2 * option[1])})
        outline_values.append(sympy.solve(subbed_equation)[0])
    print("Minimum value:", min(outline_values))
    print("Maximum value:", max(outline_values))

# ==========================
# SOLVING A RESISTOR DIVIDER
# ==========================

print("Solving resistor divider")

# The user gives us the following requirements
# Vin needs to be equal to 5v +/- 3%
# Rtotal needs to be equal to 100k +/- 10%
vin_percent_tolerance = 0.1
Rtotal_percent_tolerance = 0.1
Rtotal = 100000
V_in = 5

# Define the symbols being used
R1, R2, Vin, Vout, Rtot = sympy.symbols('R1 R2 Vin Vout Rtot')

# We have two equations that we care about in our case
equation1 = sympy.Eq(Vin, Vout * (R1 + R2) / R2)
equation2 = sympy.Eq(Rtot, R1 + R2)


# We start by computing the partial derivatives for each unset variable in each equation
# The reason we do this is because it tells us how much the tolerance impacts the final value
# Another way to say it: the partial derivative tells us how tight the tolerance needs to be for each variable
pd_r1_eq1 = sympy.diff(equation1.rhs, R1)
pd_r2_eq1 = sympy.diff(equation1.rhs, R2)
pd_r1_eq2 = sympy.diff(equation2.rhs, R1)
pd_r2_eq2 = sympy.diff(equation2.rhs, R2)

# print("Partial derivative on eq1 with resympyect to R1:", pd_r1_eq1, "R2:", pd_r2_eq1)
# print("Partial derivative on eq2 with resympyect to R1:", pd_r1_eq2, "R2:", pd_r2_eq2)

# Now let's solve the equations in the ideal case (without tolerance)
substitutes = {Vin: 5, Vout: 1.22, Rtot: Rtotal}
eq1_sub = equation1.subs(substitutes)
eq2_sub = equation2.subs(substitutes)
solutions = sympy.solve((eq1_sub, eq2_sub), (R1, R2))
# for solution in solutions:
#     print("solution for", solution, "=", solutions[solution])

# Now we evaluate the partial derivatives at the ideal solution
num_pd_r1_eq1 = abs(pd_r1_eq1.subs({Vout: 1.22, R1: solutions[R1], R2: solutions[R2]}))
num_pd_r2_eq1 = abs(pd_r2_eq1.subs({Vout: 1.22, R1: solutions[R1], R2: solutions[R2]}))

num_pd_r1_eq2 = abs(pd_r1_eq2.subs({Rtot: Rtotal, R1: solutions[R1], R2: solutions[R2]}))
num_pd_r2_eq2 = abs(pd_r2_eq2.subs({Rtot: Rtotal, R1: solutions[R1], R2: solutions[R2]}))

#print("Evaluated partial derivatives:", num_pd_r1_eq1, num_pd_r2_eq1, num_pd_r1_eq2, num_pd_r2_eq2)

rel_num_pd_r1_eq1 = num_pd_r1_eq1 * solutions[R1]/V_in
rel_num_pd_r2_eq1 = num_pd_r2_eq1 * solutions[R2]/V_in

rel_num_pd_r1_eq2 = num_pd_r1_eq2 * solutions[R1]/Rtotal
rel_num_pd_r2_eq2 = num_pd_r2_eq2 * solutions[R2]/Rtotal

# print("Relative PD of R1 in eq1:", rel_num_pd_r1_eq1, "Relative PD of R2:", rel_num_pd_r2_eq1)
# print("Relative PD of R1 in eq2:", rel_num_pd_r1_eq2, "Relative PD of R2:", rel_num_pd_r2_eq2)

# Next up, assuming the user has asked for a certain tolerance at the output,
# we need to figure out what tolernace to give to all components for that output
# tolerance to be met
# To simplify things for the moment, we assume that all components will be given the same tolerance
# In the future, we can optimize this based on the cost for a given tolerance.

tolerance_1 = math.sqrt((vin_percent_tolerance**2 * V_in**2) / (num_pd_r1_eq1**2 * solutions[R1]**2 + num_pd_r2_eq1**2 * solutions[R2]**2))
tolerance_2 = math.sqrt((Rtotal_percent_tolerance**2 * Rtotal**2) / (num_pd_r1_eq2**2 * solutions[R1]**2 + num_pd_r2_eq2**2 * solutions[R2]**2))
#print("Required tolerance to meet equation 1:", tolerance_1 * 100, "Required tolerance to meet equation 2:", tolerance_2 * 100)


# Solving with lagrangian

# Define the symbols
sigma_x1_sq = sympy.symbols('sigma_x1_sq', positive=True)
sigma_x2_sq = sympy.symbols('sigma_x2_sq', positive=True)
lambda_ = sympy.symbols('lambda_')  # Lagrange multiplier
k1, k2, sigma_y_sq = sympy.symbols('k1 k2 sigma_y_sq')  # constants


# Objective function (total cost)
# total_cost = k1 * sigma_x1_sq + k2 * sigma_x2_sq
total_cost = k_cost_resistor * sympy.sqrt(sigma_x1_sq) + k_cost_resistor * sympy.sqrt(sigma_x2_sq)
#total_cost = sigma_x1_sq**2 * sigma_x2_sq

# Constraint (output variance)
#constraint = sigma_y_sq - (num_pd_r1_eq1**2 * sigma_x1_sq + num_pd_r2_eq1**2 * sigma_x2_sq)
constraint = vin_percent_tolerance**2 - (rel_num_pd_r1_eq1**2 * sigma_x1_sq + rel_num_pd_r2_eq1**2 * sigma_x2_sq)
#constraint = 1 - sigma_x1_sq**2 - sigma_x2_sq**2

# Lagrangian
L = lambda_ * constraint - total_cost

# System of equations from the partial derivatives of L
eq1 = sympy.diff(L, sigma_x1_sq)
eq2 = sympy.diff(L, sigma_x2_sq)
eq3 = sympy.diff(L, lambda_) # here is seem that total cost disapears since it's not a function of lambda

# Solve the system of equations
solution = sympy.solve((eq1, eq2, eq3), (sigma_x1_sq, sigma_x2_sq, lambda_))

equation_outline = equation1.subs({Vout: 1.22})
for sol in solution:
    print('tolerance on R1 =', math.sqrt(sol[0])* 100)
    required_tolerance_r1 = math.sqrt(sol[0])
    print('tolerance on R2 =', math.sqrt(sol[1])* 100)
    required_tolerance_r2 = math.sqrt(sol[1])
    print_outline(R1, solutions[R1], math.sqrt(sol[0]), R2, solutions[R2], math.sqrt(sol[1]), equation_outline, Vin, V_in, vin_percent_tolerance)

#%%
# Cost function

def tolerance_cost_function_1(tolerance, cost_factor):
    return 1/(tolerance * cost_factor)

def tolerance_cost_function_2(tolerance, b, k):
    #return b + math.e**(-k*tolerance)
    var = b/tolerance
    return math.log(var) + k

def plot_inverse_function(start, end, num_points, b, k):
    # Generate x values
    x = np.linspace(start, end, num_points)

    # Avoid division by zero by removing x=0 values
    x = x[x != 0]

    # Calculate the corresponding y values
    y = []
    for value in x:
        y.append(tolerance_cost_function_2(value, b, k))

    # Create the plot
    plt.plot(x, y)

    # Set axis labels and title
    plt.xlabel('x')
    plt.ylabel('1/x')
    plt.title('Plot of 1/x')

    # Display the plot
    plt.grid(True)

# Example usage
plot_inverse_function(0, 1, 1000, 1, 1)
plot_inverse_function(0, 1, 1000, 2, 2)
plot_inverse_function(0, 1, 1000, 3, 3)
plt.ylim(0,10)
plt.show()

#%%
b_resistor = 1
k_resistor = 1
r1_cost_fc = []
r2_cost_fc = []
imp_tol = []
x = np.linspace(0, 1, 1000)

for tolerance  in x:
    r1_cost = tolerance_cost_function_2(tolerance, b_resistor, k_resistor)
    delta_to_tol_1 = tolerance - required_tolerance_r1
    delta_to_tol_2 = - math.sqrt((delta_to_tol_1**2 * rel_num_pd_r1_eq1**2) / (2 * rel_num_pd_r2_eq1**2))
    if delta_to_tol_1 < 0:
        delta_to_tol_2 *= -1

    impacted_tolerance_r2 = required_tolerance_r2 + delta_to_tol_2
    if impacted_tolerance_r2 > 0:
        r2_cost = tolerance_cost_function_2(impacted_tolerance_r2, b_resistor, k_resistor)
    else: r2_cost = 10
    r1_cost_fc.append(r1_cost)
    r2_cost_fc.append(r2_cost)
    imp_tol.append(r1_cost + r2_cost)

plt.plot(x, r1_cost_fc)
plt.plot(x, r2_cost_fc)
plt.plot(x, imp_tol)
plt.show()

#%%

# =======================
# SOLVING AN RC FILTER
# =======================

print("Solving RC filter")

R, C, FC = sympy.symbols('R C fc')
fc = 10  # Cutoff frequency in Hz
fc_tolerance = 0.1
R_value = 1000

cutoff_equration = sympy.Eq(FC, 1 / (2 * sympy.pi * R * C))
cutoff_eq = cutoff_equration.subs(FC, fc)

# Solve the equation for C
solution_for_C = sympy.solve(cutoff_eq.subs(R, R_value), C)

pd_r = sympy.diff(cutoff_eq.rhs, R)
pd_c = sympy.diff(cutoff_eq.rhs, C)

num_pd_r = abs(pd_r.subs({R: R_value, C: solution_for_C[0]}))
num_pd_c = abs(pd_c.subs({R: R_value, C: solution_for_C[0]}))

# Finding the relative partial derivative, since we are dealing with tolerances in %. See elasticity comment above.
rel_num_pd_r = num_pd_r * R_value/fc
rel_num_pd_c = num_pd_c * solution_for_C[0]/fc

# Solving with lagrangian
constraint = fc_tolerance**2 - (rel_num_pd_r**2 * sigma_x1_sq + rel_num_pd_c**2 * sigma_x2_sq)
total_cost = k_cost_resistor * sympy.sqrt(sigma_x1_sq) + k_cost_capacitor * sympy.sqrt(sigma_x2_sq)

L = lambda_ * constraint - total_cost

# System of equations from the partial derivatives of L
eq1 = sympy.diff(L, sigma_x1_sq)
eq2 = sympy.diff(L, sigma_x2_sq)
eq3 = sympy.diff(L, lambda_) # here is seem that total cost disapears since it's not a function of lambda

# Solve the system of equations
solution = sympy.solve((eq1, eq2, eq3), (sigma_x1_sq, sigma_x2_sq, lambda_))

for sol in solution:
    print('tolerance on R =', math.sqrt(sol[0])* 100)
    print('tolerance on C =', math.sqrt(sol[1])* 100)
    print_outline(C, solution_for_C[0], math.sqrt(sol[0]), R, R_value, math.sqrt(sol[1]), cutoff_equration, FC, fc, fc_tolerance)


# =======================
# SOLVING A BUTTERWORTH LC FILTER
# =======================

print("Solving LC filter")

L, C, FC = sympy.symbols('L C fc', positive=True)
fc = 1000
fc_tolerance = 0.02
omega_c = 2 * sympy.pi * fc
L_value = 10e-3  # 10 mH

# Equation for LC filter cutoff frequency
equation_lc = sympy.Eq(FC, 1/(sympy.sqrt(L*C) * 2 *sympy.pi))
eq_lc = equation_lc.subs(FC, fc)

solution_for_C = sympy.solve(eq_lc.subs(L, L_value), C)

pd_l = sympy.diff(eq_lc.rhs, L)
pd_c = sympy.diff(eq_lc.rhs, C)

num_pd_l = abs(pd_l.subs({L: L_value, C: solution_for_C[0]}))
num_pd_c = abs(pd_c.subs({L: L_value, C: solution_for_C[0]}))

# Finding the relative partial derivative, since we are dealing with tolerances in %. See elasticity comment above.
rel_num_pd_l = num_pd_l * L_value/fc
rel_num_pd_c = num_pd_c * solution_for_C[0]/fc

# Solving with lagrangian
constraint = fc_tolerance**2 - (rel_num_pd_l**2 * sigma_x1_sq + rel_num_pd_c**2 * sigma_x2_sq)
total_cost = k_cost_inductor * sympy.sqrt(sigma_x1_sq) + k_cost_capacitor * sympy.sqrt(sigma_x2_sq)

La = lambda_ * constraint - total_cost

# System of equations from the partial derivatives of L
eq1 = sympy.diff(La, sigma_x1_sq)
eq2 = sympy.diff(La, sigma_x2_sq)
eq3 = sympy.diff(La, lambda_) # here is seem that total cost disapears since it's not a function of lambda

# Solve the system of equations
solution = sympy.solve((eq1, eq2, eq3), (sigma_x1_sq, sigma_x2_sq, lambda_))

print("tolerance required at the output:", fc_tolerance * 100)
for sol in solution:
    print('tolerance on L =', math.sqrt(sol[0])* 100)
    print('tolerance on C =', math.sqrt(sol[1])* 100)
    print_outline(C, solution_for_C[0], math.sqrt(sol[0]), L, L_value, math.sqrt(sol[1]), equation_lc, FC, fc, fc_tolerance)


$$
  \int_0^\infty \frac{x^3}{e^x-1}\,dx = \frac{\pi^4}{15}
$$
# =======================
# old stuff
# =======================


# tolerance_for_r1 = vin_percent_tolerance * rel_num_pd_r1_eq1
# tolerance_for_r2 = vin_percent_tolerance * rel_num_pd_r2_eq1

# substitutes = {Vout: 1.22, R1: solutions[R1] * (1 + tolerance_1), R2: solutions[R2] * (1 - tolerance_1)}
# eq1_sub = equation1.subs(substitutes)
# test_sol = sympy.solve(eq1_sub, Vin)
# print(test_sol)
# substitutes = {Vout: 1.22, R1: solutions[R1] * (1 - tolerance_1), R2: solutions[R2] * (1 + tolerance_1)}
# eq1_sub = equation1.subs(substitutes)
# test_sol = sympy.solve(eq1_sub, Vin)
# print(test_sol)

# print(5 * (1+vin_percent_tolerance))
# print(5 * (1-vin_percent_tolerance))

# impact_r1_eq1 = num_pd_r1_eq1 / (num_pd_r1_eq1 + num_pd_r2_eq1)
# impact_r2_eq1 = num_pd_r2_eq1 / (num_pd_r1_eq1 + num_pd_r2_eq1)

# impact_r1_eq2 = num_pd_r1_eq2 / (num_pd_r1_eq2 + num_pd_r2_eq2)
# impact_r2_eq2 = num_pd_r2_eq2 / (num_pd_r1_eq2 + num_pd_r2_eq2)

# print("PD of R1 in eq1:", num_pd_r1_eq1 * 5, "PD of R2:", num_pd_r2_eq1 * 5)
# print("PD of R1 in eq2:", num_pd_r1_eq2 * Rtotal, "PD of R2:", num_pd_r2_eq2 * Rtotal)

# print("Impact of R1 in eq1:", impact_r1_eq1, "impact of R2:", impact_r2_eq1)
# print("Impact of R1 in eq2:", impact_r1_eq2, "impact of R2:", impact_r2_eq2)

# Next, we want to understand the elasticity of the variable



# # We now can understand the overall elasticity of the output value, that is, if we change all the input values
# # by a given percentage, what is the ration with which the output value will change

# total_stiffness_eq1 = (rel_num_pd_r1_eq1) + (rel_num_pd_r2_eq1)
# total_stiffness_eq2 = (rel_num_pd_r1_eq2) + (rel_num_pd_r2_eq2)

# print("Vdiv total stiffness:", (1 / total_stiffness_eq1))
# print("Rtot total stiffness:", (1 / total_stiffness_eq2))

# substitutes = {R1: solutions[R1] * (1 + tolerance_2), R2: solutions[R2] * (1 + tolerance_2)}
# eq2_sub = equation2.subs(substitutes)
# test_sol = sympy.solve(eq2_sub, Rtot)
# print(test_sol)
# substitutes = {R1: solutions[R1] * (1 - tolerance_2), R2: solutions[R2] * (1 - tolerance_2)}
# eq2_sub = equation2.subs(substitutes)
# test_sol = sympy.solve(eq2_sub, Rtot)
# print(test_sol)

# print(Rtotal * (1+Rtotal_percent_tolerance))
# print(Rtotal * (1-Rtotal_percent_tolerance))




# num_derivative_r1 = partial_derivative_r1.subs({Vin: 10, R1: 5, R2: 5})
# num_derivative_r2 = partial_derivative_r2.subs({Vin: 10, R1: 5, R2: 5})
# num_derivative_i = partial_derivative_i.subs({R: 10, I: 5})
# num_derivative_r = partial_derivative_r.subs({R: 10, I: 5})

# one_over_vdiv_total_stiffness = abs(num_derivative_r1) + abs(num_derivative_r2)
# vdiv_total_stiffness = 1/one_over_vdiv_total_stiffness
# print("Vdiv total stiffness:", vdiv_total_stiffness)

# one_over_pout_total_stiffness = abs(num_derivative_i) + abs(num_derivative_r)
# pout_total_stiffness = 1/one_over_pout_total_stiffness
# print("Pout total stiffness:", pout_total_stiffness)

# # Solve the equation with numerical values
# solutions = sympy.solve(num_equation, Vout)

# # Print the results
# # print("Solutions for Vout with numbers:")

# #print("Numerical partial derivative with resympyect to R1:", num_derivative_r1, num_derivative_r2)
# #print("Numerical partial derivative with resympyect to R:", num_derivative_i, num_derivative_r)

# print("tolerance required for Pout:", pout_total_stiffness * 10)
# print("tolerance required for Vout:", vdiv_total_stiffness * 10)


# %%
