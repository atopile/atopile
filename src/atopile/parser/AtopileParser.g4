
parser grammar AtopileParser;

options {
    superClass = AtopileParserBase ;
    tokenVocab = AtopileLexer ;
}

file_input: (NEWLINE | stmt)* EOF;

stmt: simple_stmts | compound_stmt;
simple_stmts: simple_stmt (';' simple_stmt)* ';'? NEWLINE;
simple_stmt
    : import_stmt
    | dep_import_stmt
    | assign_stmt
    | connect_stmt
    | retype_stmt
    | pindef_stmt
    | signaldef_stmt
    | assert_stmt
    | declaration_stmt
    | string_stmt
    ;

compound_stmt: blockdef;

blockdef: blocktype name ('from' name_or_attr)? ':' block;
blocktype: ('component' | 'module' | 'interface');
block: simple_stmts | NEWLINE INDENT stmt+ DEDENT;

dep_import_stmt: 'import' name_or_attr 'from' string;
import_stmt: 'from' string 'import' name_or_attr (',' name_or_attr)*;

assign_stmt: name_or_attr type_info? '=' assignable;
assignable
    : string
    | new_stmt
    | literal_physical
    | name_or_attr
    | arithmetic_expression
    ;

declaration_stmt: name_or_attr type_info;

retype_stmt: name_or_attr '->' name_or_attr;

connect_stmt: connectable '~' connectable;
connectable: name_or_attr | numerical_pin_ref | signaldef_stmt | pindef_stmt;

signaldef_stmt: 'signal' name;
pindef_stmt: 'pin' (name | totally_an_integer);

new_stmt: 'new' name_or_attr;

string_stmt: string;  // the unbound string is a statement used to add doc-strings

assert_stmt: 'assert' comparison;


// Comparison operators
// --------------------

comparison
    : arithmetic_expression compare_op_pair+
    ;

compare_op_pair
    : lt_arithmetic_or
    | gt_arithmetic_or
    | in_arithmetic_or;

lt_arithmetic_or: '<' arithmetic_expression;
gt_arithmetic_or: '>' arithmetic_expression;
in_arithmetic_or: 'within' arithmetic_expression;


// Arithmetic operators
// --------------------

arithmetic_expression
    : arithmetic_expression ('+' | '-') term
    | term
    ;

term
    : term ('*' | '/') factor
    | factor
    ;

factor
    : '+' factor
    | '-' factor
    | power;

power
    : atom ('**' factor)?
    ;


// Primary elements
// ----------------

atom
    : name_or_attr
    | literal_physical
    | arithmetic_group;

arithmetic_group
    : '(' arithmetic_expression ')';

literal_physical
    : bound_quantity
    | bilateral_quantity
    | implicit_quantity;

bound_quantity: quantity_end 'to' quantity_end;
quantity_end: NUMBER name?;
bilateral_quantity: bilateral_nominal PLUS_OR_MINUS bilateral_tolerance;
implicit_quantity: NUMBER name?;
bilateral_nominal: NUMBER name?;
bilateral_tolerance: NUMBER ('%' | name)?;

name_or_attr: attr | name;
type_info: ':' name_or_attr;
numerical_pin_ref: name_or_attr '.' totally_an_integer;
attr: name ('.' name)+;
totally_an_integer : NUMBER;
name : NAME;
string : STRING;
boolean_ : ('True' | 'False');
