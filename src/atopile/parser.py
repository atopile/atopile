import pyparsing as pp
import datamodel

# define the parser
identifier = pp.Word(pp.alphanums + "_")
value = pp.Word(pp.nums + ".") | identifier

# operators
comparison_operator = pp.oneOf("< <= == >= >")
connection_operator = pp.oneOf("~")
assignment_operator = pp.Literal("=")

pin_assignment = pp.Group("pin" + identifier)

bracketed_expression = pp.nestedExpr(opener="(", closer=")", content=pp.delimitedList(value, delim=","))
assignment_expression = pp.Group(identifier + pp.Optional("[" + identifier + "]") + assignment_operator + value)
limit_expression = pp.Group("limit" + pp.delimitedList(value + comparison_operator + value + comparison_operator + value, delim=","))
feature_declaration = pp.Group("feature" + identifier + pp.Optional("(" + pp.delimitedList(identifier) + ")") + ":")
component_declaration = pp.Group("component:")

def parse_feature(s, loc, toks):
    return datamodel.Feature(pins=[], transfer_functions=[], limits=[], states=[])

def parse_component(s, loc, toks):
    return datamodel.Component(pins=[], transfer_functions=[], types=[], limits=[], states=[], features=[])

feature_declaration.setParseAction(parse_feature)
component_declaration.setParseAction(parse_component)

language = pp.ZeroOrMore(feature_declaration | component_declaration)

# Test the parser
from pathlib import Path
with Path('examples/sandbox0-i2c.ato').open() as f:
    example = f.read()

parsed = language.parseString(example)
print(parsed)
