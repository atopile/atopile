"""
A parser for ato files.

Unfortunately, this kiiinda needs the ato_ prefix.
Otherwise importing it collides with the inbuilt `parsing` module.
"""

from sandbox import datamodel
import pyparsing as pp

identifier = pp.Word(pp.alphas + "_", pp.alphanums + "_")
value = pp.Word(pp.nums + ".", pp.alphas)

# # eg. V[abc]
# # eg. V[abc:pqr]
# real_identifier = pp.Group(identifier + "[" + pp.Group(value + pp.Optional(":" + value)) + "]")

# #%%
# # operators
# comparison_operator = pp.oneOf("< <= == >= >")
# connection_operator = pp.oneOf("~")
# assignment_operator = pp.Literal("=")

# pin_creation = pp.Group("pin" + identifier)

# generic_assignment = pp.Group(identifier + assignment_operator + value)
# model_definition = pp.Group(identifier + assignment_operator + value)

# bracketed_expression = pp.nestedExpr(opener="(", closer=")", content=pp.delimitedList(generic_assignment, delim=","))
# limit_expression = pp.Group("limit" + pp.delimitedList(value + comparison_operator + value + comparison_operator + value, delim=","))
# feature_declaration = pp.Group("feature" + identifier + pp.Optional("(" + pp.delimitedList(identifier) + ")") + ":")
# component_declaration = pp.Group("component:")

# def parse_feature(s, loc, toks):
#     return datamodel.Feature(pins=[], transfer_functions=[], limits=[], states=[])

# def parse_component(s, loc, toks):
#     return datamodel.Component(pins=[], transfer_functions=[], types=[], limits=[], states=[], features=[])

# feature_declaration.setParseAction(parse_feature)
# component_declaration.setParseAction(parse_component)

# language = pp.ZeroOrMore(feature_declaration | component_declaration)
