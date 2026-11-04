class Number:
    def __init__(self, value, raw=None):
        self.value = value
        self.raw = raw if raw is not None else str(value)


class String:
    def __init__(self, value):
        self.value = value


class Variable:
    def __init__(self, name):
        self.name = name


class BinOp:
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right


class LetDecl:
    def __init__(self, name, value):
        self.name = name
        self.value = value


class Compare:
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right


class AndCond:
    def __init__(self, conditions):
        self.conditions = conditions


class OrCond:
    def __init__(self, conditions):
        self.conditions = conditions


class IfStmt:
    def __init__(self, condition, body, else_body=None):
        self.condition = condition
        self.body = body
        self.else_body = else_body


class WhileStmt:
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body


class Assign:
    def __init__(self, name, value):
        self.name = name
        self.value = value


class PrintByte:
    def __init__(self, value, port):
        self.value = value
        self.port = port


class PrintWord:
    def __init__(self, value, port):
        self.value = value
        self.port = port


class ReadWord:
    def __init__(self, addr):
        self.addr = addr


class ReadByte:
    def __init__(self, addr):
        self.addr = addr


class Break:
    def __init__(self):
        pass


class Trap:
    def __init__(self, num):
        self.num = num


class Interrupt:
    def __init__(self, body):
        self.body = body


class Program:
    def __init__(self):
        self.statements = []

    def add(self, node):
        self.statements.append(node)


def parse_let(line, symbol_table):
    parts = line.split("=")
    var_part = parts[0].strip()
    value_part = parts[1].strip()
    var_name = var_part.replace("let ", "").strip()
    value_node = parse_expression(value_part, symbol_table)

    return LetDecl(var_name, value_node)


def print_ast(node, indent=0, file=None):
    prefix = "  " * indent

    if isinstance(node, Program):
        print(f"{prefix}Program", file=file)
        for stmt in node.statements:
            print_ast(stmt, indent + 1, file)
    elif isinstance(node, LetDecl):
        print(f"{prefix}LetDecl({node.name})", file=file)
        print_ast(node.value, indent + 1, file)
    elif isinstance(node, Number):
        print(f"{prefix}Number({node.raw})", file=file)
    elif isinstance(node, Variable):
        print(f"{prefix}Variable({node.name})", file=file)
    elif isinstance(node, BinOp):
        print(f"{prefix}BinOp({node.op})", file=file)
        print_ast(node.left, indent + 1, file)
        print_ast(node.right, indent + 1, file)
    elif isinstance(node, IfStmt):
        print(f"{prefix}IfStmt", file=file)
        print_ast(node.condition, indent + 1, file)
        if node.body:
            print(f"{prefix}  Body:", file=file)
            print_ast(node.body, indent + 2, file)
        if node.else_body:
            print(f"{prefix}  ElseBody:", file=file)
            print_ast(node.else_body, indent + 2, file)
    elif isinstance(node, Compare):
        print(f"{prefix}Compare({node.op})", file=file)
        print_ast(node.left, indent + 1, file)
        print_ast(node.right, indent + 1, file)

    elif isinstance(node, AndCond):
        print(f"{prefix}AndCond", file=file)
        for cond in node.conditions:
            print_ast(cond, indent + 1, file)

    elif isinstance(node, OrCond):
        print(f"{prefix}OrCond", file=file)
        for cond in node.conditions:
            print_ast(cond, indent + 1, file)
    elif isinstance(node, WhileStmt):
        print(f"{prefix}WhileStmt", file=file)
        print_ast(node.condition, indent + 1, file)
        if node.body:
            print(f"{prefix}  Body:", file=file)
            print_ast(node.body, indent + 2, file)
    elif isinstance(node, Assign):
        print(f"{prefix}Assign({node.name})", file=file)
        print_ast(node.value, indent + 1, file)
    elif isinstance(node, PrintByte):
        print(f"{prefix}PrintByte", file=file)
        print_ast(node.value, indent + 1, file)
        print_ast(node.port, indent + 1, file)
    elif isinstance(node, PrintWord):
        print(f"{prefix}PrintWord", file=file)
        print_ast(node.value, indent + 1, file)
        print_ast(node.port, indent + 1, file)
    elif isinstance(node, ReadWord):
        print(f"{prefix}ReadWord", file=file)
        print_ast(node.addr, indent + 1, file)
    elif isinstance(node, ReadByte):
        print(f"{prefix}ReadByte", file=file)
        print_ast(node.addr, indent + 1, file)
    elif isinstance(node, Break):
        print(f"{prefix}Break", file=file)
    elif isinstance(node, Trap):
        print(f"{prefix}Trap({node.num})", file=file)
    elif isinstance(node, Interrupt):
        print(f"{prefix}Interrupt", file=file)
        print_ast(node.body, indent + 1, file)
    elif isinstance(node, String):
        print(f"{prefix}String('{node.value}')", file=file)


def parse_expression(expr_str, symbol_table):
    expr_str = expr_str.strip()
    if expr_str.startswith("read_word("):
        addr_str = expr_str[len("read_word(") : -1].strip()
        addr_node = parse_expression(addr_str, symbol_table)
        return ReadWord(addr_node)
    elif expr_str.startswith("read_byte("):
        addr_str = expr_str[len("read_byte(") : -1].strip()
        addr_node = parse_expression(addr_str, symbol_table)
        return ReadByte(addr_node)

    if expr_str.isdigit() or expr_str.startswith("0x") or expr_str.lstrip("-").isdigit():
        try:
            return Number(int(expr_str, 0), raw=expr_str)
        except ValueError:
            pass
    elif expr_str in symbol_table:
        return Variable(expr_str)

    operators = ["+", "-", "*", "/", "%"]
    for op in operators:
        if op in expr_str:
            parts = expr_str.split(op, 1)
            left_str = parts[0].strip()
            right_str = parts[1].strip()

            left = parse_expression(left_str, symbol_table)
            right = parse_expression(right_str, symbol_table)

            return BinOp(op, left, right)
    return Variable(expr_str)


def parse_condition(cond_str, symbol_table):
    cond_str = cond_str.strip()
    operators = ["<=", ">=", "==", "!=", "<", ">"]

    for op in operators:
        if op in cond_str:
            parts = cond_str.split(op, 1)
            left_str = parts[0].strip()
            right_str = parts[1].strip()
            left = parse_expression(left_str, symbol_table)
            right = parse_expression(right_str, symbol_table)
            return Compare(op, left, right)
    raise ValueError(f"Что это ....:{cond_str}")


def parse_a_lot_of_conditions(cond_str, symbol_table):
    cond_str = cond_str.strip()
    if " and " in cond_str:
        parts = cond_str.split(" and ")
        conditions = [parse_condition(p.strip(), symbol_table) for p in parts]
        return AndCond(conditions)
    elif " or " in cond_str:
        parts = cond_str.split(" or ")
        conditions = [parse_condition(p.strip(), symbol_table) for p in parts]
        return OrCond(conditions)
    else:
        return parse_condition(cond_str, symbol_table)
