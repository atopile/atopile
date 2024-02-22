
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
    | string_stmt
    | assert_stmt
    | declaration_stmt;

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
    | name_or_attr;

declaration_stmt: name_or_attr type_info;

quantity_end: NUMBER name?;
bound_quantity: quantity_end 'to' quantity_end;
bilateral_nominal: NUMBER name?;
bilateral_tolerance: NUMBER ('%' | name)?;
bilateral_quantity: bilateral_nominal PLUS_OR_MINUS bilateral_tolerance;
implicit_quantity: NUMBER name?;
literal_physical : bound_quantity | bilateral_quantity | implicit_quantity;

retype_stmt: name_or_attr '->' name_or_attr;

connect_stmt: connectable '~' connectable;
connectable: name_or_attr | numerical_pin_ref | signaldef_stmt | pindef_stmt;

signaldef_stmt: 'signal' name;
pindef_stmt: 'pin' (name | totally_an_integer);

new_stmt: 'new' name_or_attr;

// the unbound string is a statement used to add doc-strings
string_stmt: string;

assert_stmt: ASSERTION_STRING;

name_or_attr: attr | name;
type_info: ':' name_or_attr;
numerical_pin_ref: name_or_attr '.' totally_an_integer;
attr: name ('.' name)+;
totally_an_integer : NUMBER;
name : NAME;
string : STRING;
boolean_ : ('True' | 'False');


// TODO: make a parser string that helps strip the quotes off

// ##### -- from the example Python3 parser TODO: tidy up

// All comments that start with "///" are copy-pasted from
// The Python Language Reference

// single_input: NEWLINE | simple_stmts | compound_stmt NEWLINE;
// eval_input: testlist NEWLINE* EOF;

// decorator: '@' dotted_name ( '(' arglist? ')' )? NEWLINE;
// decorators: decorator+;
// decorated: decorators (classdef | funcdef | async_funcdef);

// async_funcdef: ASYNC funcdef;
// funcdef: 'def' name parameters ('->' test)? ':' block;

// parameters: '(' typedargslist? ')';
// typedargslist: (tfpdef ('=' test)? (',' tfpdef ('=' test)?)* (',' (
//         '*' tfpdef? (',' tfpdef ('=' test)?)* (',' ('**' tfpdef ','? )? )?
//       | '**' tfpdef ','? )? )?
//   | '*' tfpdef? (',' tfpdef ('=' test)?)* (',' ('**' tfpdef ','? )? )?
//   | '**' tfpdef ','?);
// tfpdef: name (':' test)?;
// varargslist: (vfpdef ('=' test)? (',' vfpdef ('=' test)?)* (',' (
//         '*' vfpdef? (',' vfpdef ('=' test)?)* (',' ('**' vfpdef ','? )? )?
//       | '**' vfpdef (',')?)?)?
//   | '*' vfpdef? (',' vfpdef ('=' test)?)* (',' ('**' vfpdef ','? )? )?
//   | '**' vfpdef ','?
// );
// vfpdef: name;

// simple_stmts: simple_stmt (';' simple_stmt)* ';'? NEWLINE;
// simple_stmt: (expr_stmt | del_stmt | pass_stmt | flow_stmt |
//              import_stmt | global_stmt | nonlocal_stmt | assert_stmt);
// expr_stmt: testlist_star_expr (annassign | augassign (yield_expr|testlist) |
//                      ('=' (yield_expr|testlist_star_expr))*);
// annassign: ':' test ('=' test)?;
// testlist_star_expr: (test|star_expr) (',' (test|star_expr))* ','?;
// augassign: ('+=' | '-=' | '*=' | '@=' | '/=' | '%=' | '&=' | '|=' | '^=' |
//             '<<=' | '>>=' | '**=' | '//=');
// // For normal and annotated assignments, additional restrictions enforced by the interpreter
// del_stmt: 'del' exprlist;
// pass_stmt: 'pass';
// flow_stmt: break_stmt | continue_stmt | return_stmt | raise_stmt | yield_stmt;
// break_stmt: 'break';
// continue_stmt: 'continue';
// return_stmt: 'return' testlist?;
// yield_stmt: yield_expr;
// raise_stmt: 'raise' (test ('from' test)?)?;
// import_stmt: import_name | import_from;
// import_name: 'import' dotted_as_names;
// // note below: the ('.' | '...') is necessary because '...' is tokenized as ELLIPSIS
// import_from: ('from' (('.' | '...')* dotted_name | ('.' | '...')+)
//               'import' ('*' | '(' import_as_names ')' | import_as_names));
// import_as_name: name ('as' name)?;
// dotted_as_name: dotted_name ('as' name)?;
// import_as_names: import_as_name (',' import_as_name)* ','?;
// dotted_as_names: dotted_as_name (',' dotted_as_name)*;
// dotted_name: name ('.' name)*;
// global_stmt: 'global' name (',' name)*;
// nonlocal_stmt: 'nonlocal' name (',' name)*;
// assert_stmt: 'assert' test (',' test)?;

// compound_stmt: if_stmt | while_stmt | for_stmt | try_stmt | with_stmt | funcdef | classdef | decorated | async_stmt | match_stmt;
// async_stmt: ASYNC (funcdef | with_stmt | for_stmt);
// if_stmt: 'if' test ':' block ('elif' test ':' block)* ('else' ':' block)?;
// while_stmt: 'while' test ':' block ('else' ':' block)?;
// for_stmt: 'for' exprlist 'in' testlist ':' block ('else' ':' block)?;
// try_stmt: ('try' ':' block
//            ((except_clause ':' block)+
//             ('else' ':' block)?
//             ('finally' ':' block)? |
//            'finally' ':' block));
// with_stmt: 'with' with_item (',' with_item)*  ':' block;
// with_item: test ('as' expr)?;
// // NB compile.c makes sure that the default except clause is last
// except_clause: 'except' (test ('as' name)?)?;
// block: simple_stmts | NEWLINE INDENT stmt+ DEDENT;
// match_stmt: 'match' subject_expr ':' NEWLINE INDENT case_block+ DEDENT ;
// subject_expr: star_named_expression ',' star_named_expressions? | test ;
// star_named_expressions: ',' star_named_expression+ ','? ;
// star_named_expression: '*' expr | test ;
// case_block: 'case' patterns guard? ':' block ;
// guard: 'if' test ;
// patterns: open_sequence_pattern | pattern ;
// pattern: as_pattern | or_pattern ;
// as_pattern: or_pattern 'as' pattern_capture_target ;
// or_pattern: closed_pattern ('|' closed_pattern)* ;
// closed_pattern: literal_pattern | capture_pattern | wildcard_pattern | value_pattern | group_pattern | sequence_pattern | mapping_pattern | class_pattern ;
// literal_pattern: signed_number { self.CannotBePlusMinus() }? | complex_number | strings | 'None' | 'True' | 'False' ;
// literal_expr: signed_number { self.CannotBePlusMinus() }? | complex_number | strings | 'None' | 'True' | 'False' ;
// complex_number: signed_real_number '+' imaginary_number
//     | signed_real_number '-' imaginary_number
//     ;
// signed_number: NUMBER | '-' NUMBER ;
// signed_real_number: real_number | '-' real_number ;
// real_number: NUMBER ;
// imaginary_number: NUMBER ;
// capture_pattern: pattern_capture_target ;
// pattern_capture_target: /* cannot be '_' */ name { self.CannotBeDotLpEq() }? ;
// wildcard_pattern: '_' ;
// value_pattern: attr { self.CannotBeDotLpEq() }? ;
// group_pattern: '(' pattern ')' ;
// sequence_pattern:
//     '[' maybe_sequence_pattern? ']'
//     | '(' open_sequence_pattern? ')'
//     ;
// open_sequence_pattern: maybe_star_pattern ',' maybe_sequence_pattern? ;
// maybe_sequence_pattern: maybe_star_pattern (',' maybe_star_pattern)* ','? ;
// maybe_star_pattern: star_pattern | pattern ;
// star_pattern:
//     '*' pattern_capture_target
//     | '*' wildcard_pattern
//     ;
// mapping_pattern: '{' '}'
//     | '{' double_star_pattern ','? '}'
//     | '{' items_pattern ',' double_star_pattern ','? '}'
//     | '{' items_pattern ','? '}'
//     ;
// items_pattern: key_value_pattern (',' key_value_pattern)* ;
// key_value_pattern: (literal_expr | attr) ':' pattern ;
// double_star_pattern: '**' pattern_capture_target ;
// class_pattern: name_or_attr '(' ')'
//     | name_or_attr '(' positional_patterns ','? ')'
//     | name_or_attr '(' keyword_patterns ','? ')'
//     | name_or_attr '(' positional_patterns ',' keyword_patterns ','? ')'
//     ;
// positional_patterns: pattern (',' pattern)* ;
// keyword_patterns: keyword_pattern (',' keyword_pattern)* ;
// keyword_pattern: name '=' pattern ;

// test: or_test ('if' or_test 'else' test)? | lambdef;
// test_nocond: or_test | lambdef_nocond;
// lambdef: 'lambda' varargslist? ':' test;
// lambdef_nocond: 'lambda' varargslist? ':' test_nocond;
// or_test: and_test ('or' and_test)*;
// and_test: not_test ('and' not_test)*;
// not_test: 'not' not_test | comparison;
// comparison: expr (comp_op expr)*;
// // <> isn't actually a valid comparison operator in Python. It's here for the
// // sake of a __future__ import described in PEP 401 (which really works :-)
// comp_op: '<'|'>'|'=='|'>='|'<='|'<>'|'!='|'in'|'not' 'in'|'is'|'is' 'not';
// star_expr: '*' expr;
// expr: xor_expr ('|' xor_expr)*;
// xor_expr: and_expr ('^' and_expr)*;
// and_expr: shift_expr ('&' shift_expr)*;
// shift_expr: arith_expr (('<<'|'>>') arith_expr)*;
// arith_expr: term (('+'|'-') term)*;
// term: factor (('*'|'@'|'/'|'%'|'//') factor)*;
// factor: ('+'|'-'|'~') factor | power;
// power: atom_expr ('**' factor)?;
// atom_expr: AWAIT? atom trailer*;
// atom: '(' (yield_expr|testlist_comp)? ')'
//    | '[' testlist_comp? ']'
//    | '{' dictorsetmaker? '}'
//    | name | NUMBER | STRING+ | '...' | 'None' | 'True' | 'False' ;
// name : NAME | '_' | 'match' ;
// testlist_comp: (test|star_expr) ( comp_for | (',' (test|star_expr))* ','? );
// trailer: '(' arglist? ')' | '[' subscriptlist ']' | '.' name ;
// subscriptlist: subscript_ (',' subscript_)* ','?;
// subscript_: test | test? ':' test? sliceop?;
// sliceop: ':' test?;
// exprlist: (expr|star_expr) (',' (expr|star_expr))* ','?;
// testlist: test (',' test)* ','?;
// dictorsetmaker: ( ((test ':' test | '**' expr)
//                    (comp_for | (',' (test ':' test | '**' expr))* ','?)) |
//                   ((test | star_expr)
//                    (comp_for | (',' (test | star_expr))* ','?)) );

// classdef: 'class' name ('(' arglist? ')')? ':' block;

// arglist: argument (',' argument)* ','?;

// // The reason that keywords are test nodes instead of NAME is that using NAME
// // results in an ambiguity. ast.c makes sure it's a NAME.
// // "test '=' test" is really "keyword '=' test", but we have no such token.
// // These need to be in a single rule to avoid grammar that is ambiguous
// // to our LL(1) parser. Even though 'test' includes '*expr' in star_expr,
// // we explicitly match '*' here, too, to give it proper precedence.
// // Illegal combinations and orderings are blocked in ast.c:
// // multiple (test comp_for) arguments are blocked; keyword unpackings
// // that precede iterable unpackings are blocked; etc.
// argument: ( test comp_for? |
//             test '=' test |
//             '**' test |
//             '*' test );

// comp_iter: comp_for | comp_if;
// comp_for: ASYNC? 'for' exprlist 'in' or_test comp_iter?;
// comp_if: 'if' test_nocond comp_iter?;

// // not used in grammar, but may appear in "node" passed from Parser to Compiler
// encoding_decl: name;

// yield_expr: 'yield' yield_arg?;
// yield_arg: 'from' test | testlist;

// strings: STRING+ ;
