# Лаб 4 

- Розова Елена Алексеевна P3210
- `alg | cisc | neum | hw | trap | mem | pstr | cache | alg1`


## Язык программирования
```bnf
<program>      ::= "interrupt" "{" <stmt_list> "}" <stmt_list>
<stmt_list>    ::= <stmt> | <stmt> <stmt_list> | ε
<stmt>         ::= <let_decl> | <assign> | <if_stmt> | <while_stmt> | <print_stmt>
<let_decl>     ::= "let" <var> "=" <expr>
<assign>       ::= <var> "=" <expr>
<if_stmt>      ::= "if" "(" <cond> ")" "{" <stmt_list> "}" ["else" "{" <stmt_list> "}"]
<while_stmt>   ::= "while" "(" <cond> ")" "{" <stmt_list> "}"
<print_stmt>   ::= "print_byte" "(" <expr> "," <expr> ")"
<cond>         ::= <expr> <cmp_op> <expr>
<cmp_op>       ::= "==" | "!=" | "<" | ">" | "<=" | ">="
<expr>         ::= <number> | <var> | <read_call> | <expr> <arith_op> <expr>
<arith_op>     ::= "+" | "-" | "*" | "/" | "%" | "&" | "|"
<read_call>    ::= "read_byte" "(" <expr> ")"
<var>          ::= [a-zA-Z_][a-zA-Z0-9_]*
<number>       ::= [0-9]+ | "0x"[0-9A-Fa-f]+
```
