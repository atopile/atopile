// $antlr-format indentWidth 4
// $antlr-format useTab false
// $antlr-format columnLimit 89
// $antlr-format allowShortBlocksOnASingleLine true
// $antlr-format allowShortRulesOnASingleLine false
// $antlr-format alignSemicolons hanging
// $antlr-format alignColons hanging

parser grammar AtoParser;

options {
    superClass = AtoParserBase;
    tokenVocab = AtoLexer;
}

file_input
    : (NEWLINE | stmt)* EOF
    ;

stmt
    : simple_stmts
    | compound_stmt
    ;
simple_stmts
    : simple_stmt (';' simple_stmt)* ';'? NEWLINE
    ;
simple_stmt
    : import_stmt
    | dep_import_stmt
    | assign_stmt
    | cum_assign_stmt
    | set_assign_stmt
    | connect_stmt
    | retype_stmt
    | pin_declaration
    | signaldef_stmt
    | assert_stmt
    | declaration_stmt
    | string_stmt
    | pass_stmt
    ;

compound_stmt
    : blockdef
    ;

blockdef
    : blocktype name blockdef_super? ':' block
    ;
// TODO @v0.4 consider ()
blockdef_super
    : 'from' type_reference
    ;
// TODO @v0.4 consider removing component (or more explicit code-as-data)
blocktype
    : ('component' | 'module' | 'interface')
    ;
block
    : simple_stmts
    | NEWLINE INDENT stmt+ DEDENT
    ;

// TODO: @v0.4 remove the deprecated import form
dep_import_stmt
    : 'import' type_reference 'from' string
    ;
import_stmt
    : ('from' string)? 'import' type_reference (
        ',' type_reference
    )*
    ;

declaration_stmt
    : field_reference type_info
    ;
field_reference_or_declaration
    : field_reference
    | declaration_stmt
    ;
assign_stmt
    : field_reference_or_declaration '=' assignable
    ;
cum_assign_stmt
    : field_reference_or_declaration cum_operator cum_assignable
    ;
// TODO: consider sets cum operator
set_assign_stmt
    : field_reference_or_declaration ('|=' | '&=') cum_assignable
    ;
cum_operator
    : '+='
    | '-='
    ;
cum_assignable
    : literal_physical
    | arithmetic_expression
    ;

assignable
    : string
    | new_stmt
    | literal_physical
    | arithmetic_expression
    | boolean_
    ;

retype_stmt
    : field_reference '->' type_reference
    ;

connect_stmt
    : connectable '~' connectable
    ;
connectable
    : field_reference
    | signaldef_stmt
    | pindef_stmt
    ;

signaldef_stmt
    : 'signal' name
    ;
pindef_stmt
    : pin_stmt
    ;
pin_declaration
    : pin_stmt
    ;
pin_stmt
    : 'pin' (name | totally_an_integer | string)
    ;

new_stmt
    : 'new' type_reference
    ;

string_stmt
    : string
    ; // the unbound string is a statement used to add doc-strings

pass_stmt
    : 'pass'
    ; // the unbound string is a statement used to add doc-strings

assert_stmt
    : 'assert' comparison
    ;

// Comparison operators --------------------

comparison
    : arithmetic_expression compare_op_pair+
    ;

compare_op_pair
    : lt_arithmetic_or
    | gt_arithmetic_or
    | lt_eq_arithmetic_or
    | gt_eq_arithmetic_or
    | in_arithmetic_or
    | is_arithmetic_or
    ;

lt_arithmetic_or
    : '<' arithmetic_expression
    ;
gt_arithmetic_or
    : '>' arithmetic_expression
    ;
lt_eq_arithmetic_or
    : '<=' arithmetic_expression
    ;
gt_eq_arithmetic_or
    : '>=' arithmetic_expression
    ;
in_arithmetic_or
    : 'within' arithmetic_expression
    ;
is_arithmetic_or
    : 'is' arithmetic_expression
    ;

// Arithmetic operators --------------------

arithmetic_expression
    : arithmetic_expression ('|' | '&') sum
    | sum
    ;

sum
    : sum ('+' | '-') term
    | term
    ;

term
    : term ('*' | '/') power
    | power
    ;

power
    : functional ('**' functional)?
    ;

functional
    : bound
    | name '(' bound+ ')'
    ;

bound
    : atom
    ;

// Primary elements ----------------

atom
    : field_reference
    | literal_physical
    | arithmetic_group
    ;

arithmetic_group
    : '(' arithmetic_expression ')'
    ;

literal_physical
    : bound_quantity
    | bilateral_quantity
    | quantity
    ;

bound_quantity
    : quantity 'to' quantity
    ;
bilateral_quantity
    : quantity PLUS_OR_MINUS bilateral_tolerance
    ;
quantity
    : ('+' | '-')? NUMBER name?
    ;
bilateral_tolerance
    : NUMBER ('%' | name)?
    ;

key
    : NUMBER
    ;
array_index
    : '[' key ']'
    ;

// backwards compatibility for A.1
pin_reference_end
    : '.' NUMBER
    ;
field_reference_part
    : name array_index?
    ;
field_reference
    : field_reference_part ('.' field_reference_part)* pin_reference_end?
    ;
type_reference
    : name ('.' name)*
    ;
// TODO better unit
unit
    : name
    ;
type_info
    : ':' unit
    ;
totally_an_integer
    : NUMBER
    ;
name
    : NAME
    ;
string
    : STRING
    ;
boolean_
    : ('True' | 'False')
    ;