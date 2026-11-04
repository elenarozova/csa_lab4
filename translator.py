import sys

from ast_parser import Assign, Break, IfStmt, Interrupt, LetDecl, Number, PrintByte, PrintWord, Program, String, Trap, WhileStmt, parse_a_lot_of_conditions, parse_expression, parse_let, print_ast

symbol_table = {"count": 0x3000}  
var_addr = 0x3004  
if_counter = 0
while_counter = 0
block = []
current_if_label = ""
current_if_stmt = None
flag_for_if = 0
in_interrupt = False
output_lines = []
program_ast = Program()
context_stack = [program_ast]

def add_to_current_context(node):
    context_stack[-1].add(node)

def printl(line):
    output_lines.append(line)

def translate(input_file, output_file):
    global flag_for_if, in_interrupt
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('//'): 
                continue

            if line.startswith("interrupt"):
                in_interrupt = True
                printl("org 0x00")
                printl("store [0x0088], r0")
                printl("store [0x008C], r1")
                printl("store [0x0090], r2")
                printl("store [0x0094], r3")
                interrupt_body = Program()
                context_stack.append(interrupt_body)
                continue


            elif line == '}' and in_interrupt:
                in_interrupt = False
                printl("load r0, [0x0088]")
                printl("load r1, [0x008C]")
                printl("load r2, [0x0090]")
                printl("load r3, [0x0094]")
                printl("reti")
                printl("org 0x100") 
                printl("int_enable")
                int_body = context_stack.pop()
                int_node = Interrupt(int_body)
                program_ast.statements.insert(0, int_node)
                continue
            
            if line.startswith('}'):
                if (flag_for_if != 0): do_decide(line)  
                end_op()
                line = line.replace('}', '').strip()
                if not line:
                    continue
            if (flag_for_if != 0): do_decide(line)
            
            

            if line.startswith('let'): do_let(line)
            elif line.startswith('while'): do_while(line)
            elif line.startswith('if'): do_if(line)
            elif line.startswith("break"): do_break()
            elif line.startswith("print_word"): do_print(line)
            elif line.startswith("print_byte"): do_print(line)
            #elif line.replace("}", "").strip().startswith('else'): do_else()
            elif '=' in line: do_change_value(line)

    if (flag_for_if != 0): printl(f"{flag_for_if}:")
    printl("halt")
    with open('program_ast.txt', 'w') as f:
        print_ast(program_ast, file=f)
    with open(output_file, 'w') as f:
        f.write('\n'.join(output_lines))

def do_let(line):
    global var_addr, symbol_table

    parts = line.split('=', 1)  
    var_part = parts[0].strip()  
    value_part = parts[1].strip()
    var_name = var_part.replace('let ', '').strip()
    current_addr = var_addr
    symbol_table[var_name] = current_addr
    if value_part.startswith('"') and value_part.endswith('"'):
        text = value_part[1:-1]
        string_node = String(text)
        let_node = LetDecl(var_name, string_node)
        add_to_current_context(let_node)
        var_addr = put_pstr(text, current_addr)
        return
    var_addr = var_addr + 4
    value_node = parse_expression(value_part, symbol_table)
    let_node = LetDecl(var_name, value_node)
    add_to_current_context(let_node)
    if(do_if_math(value_part, "r0") == 0):
        load_operand(value_part, "r0")
       
    printl(f"store [0x{symbol_table[var_name]:04X}], r0")

def put_pstr(text, current_addr):
    lenght = len(text)
    printl(f"load r0, #{lenght}")
    printl(f"store_byte [0x{current_addr:04X}], r0")
    for i in range(0, len(text)):
        addr = current_addr+i+1
        ascii_n = ord(text[i])
        printl(f"load r0, #{ascii_n}")
        printl(f"store_byte [0x{addr:04X}], r0")
    return current_addr+lenght+1

def load_operand(value, register):
    if ("read_word" in value) or ("read_byte" in value):
        if in_interrupt:
            printl(f"load {register}, R_INT")
            return
        value_m = value.split('(')
        addr = value_m[1].strip().replace(")","")
        if do_if_math(addr, "r1") == 0:
            load_operand(addr, "r1")
        if "read_byte" in value:
            printl(f"load_byte {register}, [r1]")
        else:
            printl(f"load {register}, [r1]")

    elif (value.lstrip('-').isdigit() or value.startswith('0x')):
        printl(f"load {register}, #{value}")
    else:
        printl(f"load {register}, [0x{symbol_table[value]:04X}]")

def do_if_math(line, reg = "r0"):
    oper = None
    str_oper = None
    if line.startswith('-'):
        return 0
    if "read_byte(" in line or "read_word(" in line:
        return 0
    if ">>" in line:
        parts = line.split(">>")
        if len(parts) != 2:
            print(f"Ошибка: некорректный оператор >> в выражении '{line}'")
            sys.exit(1)
        sec_oper = parts[1].strip()
        if sec_oper.startswith('-'):
            print(f"Ошибка: сдвиг на отрицательное число запрещён ('{line}')")
            sys.exit(1)
        if not (sec_oper.isdigit() or sec_oper.startswith('0x')):
            print(f"Ошибка: сдвигать можно только на константу ('{line}')")
            sys.exit(1)
        oper = ">>"
        str_oper = "lsr"

    elif "<<" in line:
        parts = line.split("<<")
        if len(parts) != 2:
            print(f"Ошибка: некорректный оператор << в выражении '{line}'")
            sys.exit(1)
        sec_oper = parts[1].strip()
        if sec_oper.startswith('-'):
            print(f"Ошибка: сдвиг на отрицательное число запрещён ('{line}')")
            sys.exit(1)
        if not (sec_oper.isdigit() or sec_oper.startswith('0x')):
            print(f"Ошибка: сдвигать можно только на константу ('{line}')")
            sys.exit(1)
        oper = "<<"
        str_oper = "lsl"

    if ("&" in line):
        oper = "&"
        str_oper = "and"
    elif ("|" in line):
        oper = "|"
        str_oper = "or"
    elif ("+" in line ):
        oper = "+"
        str_oper = "add"
    elif ("-" in line ):
        oper = "-"
        str_oper = "sub"
    elif ("/" in line):
        oper = "/"
        str_oper = "div"
    elif ("*" in line):
        oper = "*"
        str_oper = "mul"
    elif ("%" in line):
        oper = "%"
        str_oper = "mod"
    elif '=' in line: return 0
    if oper is None:
        return 0
    operands = line.strip().split(oper)
    left = operands[0].strip()
    right = operands[1].strip()
    
    if (do_if_math(left, reg)==0):
            load_operand(left, reg)
    if (oper!=">>" and oper!="<<"):
        if (do_if_math(right, "r3")==0):
            load_operand(right, "r3")
        printl(f"{str_oper} {reg}, {reg}, r3")
    else:
        printl(f"{str_oper} {reg}, {reg}, #{right}")
    return 1

def do_if(line):
    global if_counter, flag_for_if

    condition = line.split('(')[1].split(')')[0].strip()
    condition_ast = parse_a_lot_of_conditions(condition, symbol_table)
    if_body = Program()
    if_stmt = IfStmt(condition_ast, None)
    add_to_current_context(if_stmt)
    context_stack.append(if_body)
    check_condition(condition, f"else_{if_counter}")
    
    block.append(["if", if_counter, if_stmt])
    if_counter+=1

def do_else():
    global flag_for_if
    else_body = Program()
    context_stack.append(else_body)
    num = flag_for_if.split("_")[2]
    block.append(["else",num , current_if_stmt])
    printl(f"jmp {flag_for_if}")
    printl(f"else_{num}:")
    flag_for_if = 0 

def do_while(line):
    global while_counter
    condition = line.split('(')[1].split(')')[0].strip()
    condition_ast = parse_a_lot_of_conditions(condition, symbol_table)
    while_body = Program()
    
    while_stmt = WhileStmt(condition_ast, None)
    add_to_current_context(while_stmt)
    context_stack.append(while_body)
    printl(f"while_{while_counter}:")
    check_condition(condition, f"end_while_{while_counter}")
    block.append(["while", while_counter, while_stmt])
    while_counter += 1

def do_break():
    add_to_current_context(Break())
    for i in range(len(block)-1, -1, -1):
        if block[i][0] == "while":
            printl(f"jmp end_while_{block[i][1]}")
            return

def do_print(line):
    args_str = line.split('(')[1].split(')')[0]
    args = args_str.split(',')
    value = args[0].strip() 
    port = args[1].strip()
    if do_if_math(value, "r0") == 0:
        load_operand(value, "r0")
    value_node = parse_expression(value, symbol_table)
    port_node = parse_expression(port, symbol_table)
    if "print_byte" in line:
        add_to_current_context(PrintByte(value_node, port_node))
    else:
        add_to_current_context(PrintWord(value_node, port_node))
    
    if "+" in port:
        parts = port.split('+')
        base = parts[0].strip()      
        var_name = parts[1].strip()  
        var_addr = symbol_table[var_name]
        printl(f"load r1, [0x{var_addr:04X}]")
        if "print_byte" in line:
            printl(f"store_byte [{base}+r1], r0")
        else:
            printl(f"store [{base}+r1], r0")
    else:
        if port.startswith('0x') or port.isdigit():
            if "print_byte" in line:
                printl(f"store_byte [{port}], r0")
            else:
                printl(f"store [{port}], r0")
        else:
            printl(f"load r1, [0x{symbol_table[port]:04X}]")
            if "print_byte" in line:
                printl(f"store_byte [r1], r0")             
            else:
                printl(f"store [r1], r0")                 


def do_change_value(line):
    parts = line.split("=")
    var_name = parts[0].strip()
    value_part = parts[1].strip()
    addr = symbol_table[var_name]
    value_node = parse_expression(value_part, symbol_table)
    assign_node = Assign(var_name, value_node)
    add_to_current_context(assign_node)
    if (do_if_math(value_part, "r0") == 0):
        load_operand(value_part, "r0")
    printl(f"store [0x{addr:04X}], r0")

def do_decide(line):
    global flag_for_if
    if (line.startswith('else')):
        do_else()
    else:
        num = flag_for_if.split("_")[2]
        printl(f"else_{num}:")
        printl(f"{flag_for_if}:")  
    flag_for_if = 0


def end_op():
    global flag_for_if, current_if_stmt
    if not block:
        return
    end_block = block.pop()
    end_block_type = end_block[0]
    end_block_number = end_block[1]

    if(end_block_type == "if"):
        if_stmt = end_block[2] 
        if_body = context_stack.pop()
        if_stmt.body = if_body
        current_if_stmt = if_stmt
        flag_for_if = f"end_if_{end_block_number}"
    elif (end_block_type == "else"):
        if_stmt = end_block[2]
        else_body = context_stack.pop()
        if_stmt.else_body = else_body
        printl(f"end_if_{end_block_number}:")  
    elif (end_block_type == "while"):
        while_stmt = end_block[2]
        while_body = context_stack.pop()
        while_stmt.body = while_body
        printl(f"jmp while_{end_block_number}")
        printl(f"end_while_{end_block_number}:")

def check_condition(condition, label):
    if (" and " in condition) and (" or " in condition):
        print(f"Ошибка: нельзя смешивать 'and' и 'or' в одном условии. Используйте вложенные if.")
        sys.exit(1)
    if (" and " in condition):
        operands = condition.split(" and ")
        for i in operands:
            oper = i.strip()
            do_condition(oper, label, jump_if_false=True)
    elif (" or " in condition):
        body_label = label.replace("else_", "body_")
        operands = condition.split(" or ")
        for part in operands:
            do_condition(part.strip(), body_label, jump_if_false=False)
        printl(f"jmp {label}")
        printl(f"{body_label}:") 
    else:
        do_condition(condition, label, jump_if_false=True)

def do_condition(condition, label, jump_if_false=True):
    if "<<" in condition or ">>" in condition:
        print(f"Ошибка: побитовые сдвиги (<<, >>) не поддерживаются в условиях. Разбейте выражение на несколько let.")
        sys.exit(1)
    
    if ("<" in condition ):
        oper = "<"
        str_oper1 = "jgt"
        str_oper2 = "jeq"
        if ("=" in condition):
            oper = "<="
            str_oper1 = "jgt"
            str_oper2 = 0
    elif (">" in condition):
        oper = ">"
        str_oper1 = "jlt"
        str_oper2 = "jeq"
        if ("=" in condition):
            oper = ">="
            str_oper1 = "jlt"
            str_oper2 = 0
    elif ("==" in condition):
        oper = "=="
        str_oper1 = "jne"
        str_oper2 = 0
    elif ("!=" in condition):
        oper = "!="
        str_oper1 = "jeq"
        str_oper2 = 0

    conditions = condition.split(oper)
    left = conditions[0].strip()
    right = conditions[1].strip()
    if (do_if_math(left, "r0")==0):
        load_operand(left, "r0")
    if (do_if_math(right,"r2")==0):
        load_operand(right, "r2")
    printl("cmp r0, r2")

    if jump_if_false:
        printl(f"{str_oper1} {label}")
        if (str_oper2!=0):
            printl(f"{str_oper2} {label}")
    else:
        if oper == "<":
            printl(f"jlt {label}")
        elif oper == "<=":
            printl(f"jlt {label}")
            printl(f"jeq {label}")
        elif oper == ">":
            printl(f"jgt {label}")
        elif oper == ">=":
            printl(f"jgt {label}")
            printl(f"jeq {label}")
        elif oper == "==":
            printl(f"jeq {label}")
        elif oper == "!=":
            printl(f"jne {label}")



if __name__ == '__main__':
       if len(sys.argv) > 1:
           input_file = sys.argv[1]
       else:
           input_file = 'program.kot'            
       translate(input_file, 'program.asm')