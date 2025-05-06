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

pragma_stmt
    : PRAGMA
    ;

stmt
    : simple_stmts
    | compound_stmt
    | pragma_stmt
    ;
simple_stmts
    : simple_stmt (SEMI_COLON simple_stmt)* SEMI_COLON? NEWLINE
    ;
simple_stmt
    : import_stmt
    | dep_import_stmt
    | assign_stmt
    | cum_assign_stmt
    | set_assign_stmt
    | connect_stmt
    | directed_connect_stmt
    | retype_stmt
    | pin_declaration
    | signaldef_stmt
    | assert_stmt
    | declaration_stmt
    | string_stmt
    | pass_stmt
    | trait_stmt
    ;

compound_stmt
    : blockdef
    | for_stmt
    ;

blockdef
    : blocktype name blockdef_super? COLON block
    ;
// TODO @v0.4 consider ()
blockdef_super
    : FROM type_reference
    ;
// TODO @v0.4 consider removing component (or more explicit code-as-data)
blocktype
    : (COMPONENT | MODULE | INTERFACE)
    ;
block
    : simple_stmts
    | NEWLINE INDENT stmt+ DEDENT
    ;

// TODO: @v0.4 remove the deprecated import form
dep_import_stmt
    : IMPORT type_reference FROM string
    ;
import_stmt
    : (FROM string)? IMPORT type_reference (
        COMMA type_reference
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
    : field_reference_or_declaration (
        OR_ASSIGN
        | AND_ASSIGN
    ) cum_assignable
    ;
cum_operator
    : ADD_ASSIGN
    | SUB_ASSIGN
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
    : field_reference ARROW type_reference
    ;

directed_connect_stmt
    // only one type of SPERM per stmt allowed. both here for better error messages
    : bridgeable ((SPERM | LSPERM) bridgeable)+
    ;
connect_stmt
    : mif WIRE mif
    ;
bridgeable
    : connectable
    ;
mif
    : connectable
    ;
connectable
    : field_reference
    | signaldef_stmt
    | pindef_stmt
    ;

signaldef_stmt
    : SIGNAL name
    ;
pindef_stmt
    : pin_stmt
    ;
pin_declaration
    : pin_stmt
    ;
pin_stmt
    : PIN (name | number_hint_natural | string)
    ;

new_stmt
    : NEW type_reference ('[' new_count ']')? template?
    ;
new_count
    : number_hint_natural
    ;

string_stmt
    : string
    ; // the unbound string is a statement used to add doc-strings

pass_stmt
    : PASS
    ; // the unbound string is a statement used to add doc-strings

list_literal_of_field_references
    : '[' (
        field_reference (COMMA field_reference)* COMMA?
    )? ']'
    ;

iterable_references
    : field_reference slice?
    | list_literal_of_field_references
    ;

for_stmt
    : FOR name IN iterable_references COLON block
    ;

assert_stmt
    : ASSERT comparison
    ;

trait_stmt
    // TODO: move namespacing to type_reference
    : TRAIT type_reference (DOUBLE_COLON constructor)? template?
    ;
constructor
    : name
    ;
template
    : '<' (template_arg (COMMA template_arg)* COMMA?)? '>'
    ;
template_arg
    : name ASSIGN literal
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
    : LESS_THAN arithmetic_expression
    ;
gt_arithmetic_or
    : GREATER_THAN arithmetic_expression
    ;
lt_eq_arithmetic_or
    : LT_EQ arithmetic_expression
    ;
gt_eq_arithmetic_or
    : GT_EQ arithmetic_expression
    ;
in_arithmetic_or
    : WITHIN arithmetic_expression
    ;
is_arithmetic_or
    : IS arithmetic_expression
    ;

// Arithmetic operators --------------------

arithmetic_expression
    : arithmetic_expression (OR_OP | AND_OP) sum
    | sum
    ;

sum
    : sum (PLUS | MINUS) term
    | term
    ;

term
    : term (STAR | DIV) power
    | power
    ;

power
    : functional (POWER functional)?
    ;

functional
    : bound
    | name '(' bound+ ')'
    ;

bound
    : atom
    ;

// Primary elements ----------------

slice
    : '[' (
        slice_start? COLON slice_stop? (COLON slice_step?)?
    )? ']'
    // else [::step] wouldn't match
    | '[' ( DOUBLE_COLON slice_step?) ']'
    ;
slice_start
    : number_hint_integer
    ;
slice_stop
    : number_hint_integer
    ;
slice_step
    : number_hint_integer
    ;

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
    : quantity TO quantity
    ;
bilateral_quantity
    : quantity PLUS_OR_MINUS bilateral_tolerance
    ;
quantity
    : number name?
    ;
bilateral_tolerance
    : number_signless (PERCENT | name)?
    ;

key
    : number_hint_integer
    ;
array_index
    : '[' key ']'
    ;

// backwards compatibility for A.1
pin_reference_end
    : DOT number_hint_natural
    ;
field_reference_part
    : name array_index?
    ;
field_reference
    : field_reference_part (DOT field_reference_part)* pin_reference_end?
    ;
type_reference
    : name (DOT name)*
    ;
// TODO better unit
unit
    : name
    ;
type_info
    : COLON unit
    ;
name
    : NAME
    ;

// Literals
literal
    : string
    | boolean_
    | number
    ;

string
    : STRING
    ;
boolean_
    : TRUE
    | FALSE
    ;
number_hint_natural
    : number_signless
    ;
number_hint_integer
    : number
    ;
number
    : (PLUS | MINUS)? number_signless
    ;
number_signless
    : NUMBER
    ;