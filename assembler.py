import sys


class ParsedInstruction:
    def __init__(self, addr, mnemonic, operands, raw_line):
        self.address = addr
        self.mnemonic = mnemonic
        self.operands = operands
        self.raw_line = raw_line


OPCODES = {
    "add": 0x00,
    "sub": 0x01,
    "adc": 0x02,
    "mul": 0x03,
    "div": 0x04,
    "mod": 0x05,
    "and": 0x06,
    "or": 0x07,
    "lsl": 0x08,
    "lsr": 0x09,
    "load": 0x10,
    "store": 0x11,
    "load_byte": 0x12,
    "store_byte": 0x13,
    "cmp": 0x20,
    "jmp": 0x30,
    "jeq": 0x31,
    "jne": 0x32,
    "jlt": 0x33,
    "jgt": 0x34,
    "int_enable": 0x40,
    "int_disable": 0x41,
    "reti": 0x42,
    "halt": 0x43,
}


def assemble(input_file, output_bin, output_log):
    labels, instructions = go_first(input_file)
    print(f"Метки: {labels}")
    print(f"Инструкций: {len(instructions)}")
    data = bytearray(0x10000)
    log_lines = []
    for instr in instructions:
        bytes_list = encode_instruction(instr, labels)
        addr = instr.address
        for i, byte in enumerate(bytes_list):
            data[addr + i] = byte
        hex_code = " ".join(f"{b:02X}" for b in bytes_list)
        line = f"{instr.address:04X} - {hex_code:<15} - {instr.raw_line}"
        log_lines.append(line)
    with open(output_bin, "wb") as f:
        f.write(data)
    with open(output_log, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")


def go_first(input_file):
    labels = {}
    instructions = []
    current_addr = 0
    with open(input_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            if line.startswith("org"):
                addr = line.replace("org", "").strip()
                current_addr = int(addr, 16) if addr.startswith("0x") else int(addr)
                continue

            if ":" in line:
                label_part, rest = line.split(":", 1)
                labels[label_part.strip()] = current_addr
                line = rest.strip()
                if not line:
                    continue
            parts = line.split()
            if parts:
                mnemonic = parts[0]
                raw = parts[1:] if len(parts) > 1 else []
                instr = ParsedInstruction(current_addr, mnemonic, raw, line)
                instructions.append(instr)
                instr_len = calculate_length(mnemonic, raw)
                current_addr += instr_len
    return labels, instructions


def parse_oper(op_str, labels):
    op_str = op_str.strip()
    if op_str.upper() == "R_INT":
        return (0, 15)
    if op_str.startswith("r") and op_str[1:].isdigit():
        reg_num = int(op_str[1:])
        return (0, reg_num)
    if op_str.startswith("#"):
        num_str = op_str[1:]
        if num_str.startswith("0x"):
            num = int(num_str, 16)
        else:
            num = int(num_str)
        if -128 <= num <= 127:
            return (1, num)
        else:
            return (2, num)
    if op_str.startswith("[") and op_str.endswith("]"):
        inner = op_str[1:-1]
        if "+" in inner:
            parts = inner.split("+")
            part1 = parts[0].strip()
            part2 = parts[1].strip()
            if part1.startswith("r") and len(part1) > 1 and part1[1:].isdigit():
                if part2.startswith("r") and len(part2) > 1 and part2[1:].isdigit():
                    reg_base = int(part1[1:])
                    reg_idx = int(part2[1:])
                    return (5, (reg_base << 4) | reg_idx)
                else:
                    reg = int(part1[1:])
                    addr = parse_address(part2, labels)
                    return (6, (reg << 16) | addr)
            elif part2.startswith("r") and len(part2) > 1 and part2[1:].isdigit():
                reg = int(part2[1:])
                addr = parse_address(part1, labels)
                return (6, (reg << 16) | addr)
            else:
                addr = parse_address(part1, labels) + parse_address(part2, labels)
                return (6, addr)
        if inner.startswith("r") and inner[1:].isdigit():
            reg_num = int(inner[1:])
            return (4, reg_num)
        if inner.startswith("0x"):
            addr = int(inner, 16)
        elif inner.isdigit():
            addr = int(inner)
        elif inner in labels:
            addr = labels[inner]
        else:
            addr = 0
        return (3, addr)
    if op_str in labels:
        return (3, labels[op_str])
    return (0, 0)


def parse_address(addr_str, labels):
    addr_str = addr_str.strip()
    if addr_str.startswith("0x"):
        return int(addr_str, 16)
    elif addr_str.isdigit():
        return int(addr_str)
    elif addr_str in labels:
        return labels[addr_str]
    else:
        return 0


def get_operand_mode(op_str):
    op_str = op_str.strip().rstrip(",")
    if op_str.upper() == "R_INT":
        return 0
    if op_str.startswith("r") and op_str[1:].isdigit():
        return 0
    if op_str.startswith("#"):
        num_str = op_str[1:]
        num = int(num_str, 16) if num_str.startswith("0x") else int(num_str)
        if -128 <= num <= 127:
            return 1  # 8 бит
        else:
            return 2
    if op_str.startswith("[") and op_str.endswith("]"):
        inner = op_str[1:-1]
        if "+" in inner:
            parts = inner.split("+")
            p1 = parts[0].strip()
            p2 = parts[1].strip()
            p1_is_reg = p1.startswith("r") and p1[1:].isdigit()
            p2_is_reg = p2.startswith("r") and p2[1:].isdigit()
            if p1_is_reg and p2_is_reg:
                return 5  # [rN + rM]
            else:
                return 6  # [addr + rN]
        if inner.startswith("r") and inner[1:].isdigit():
            return 4  # [rN]
        return 3  # [addr]
    return 3


def calculate_length(mnemonic, raw):
    if mnemonic in ["halt", "reti", "int_enable", "int_disable"]:
        return 1
    if mnemonic in ["jmp", "jeq", "jne", "jlt", "jgt"]:
        return 3
    if not raw:
        return 3
    if mnemonic in ["store", "store_byte"]:
        mode = get_operand_mode(raw[0])
    elif mnemonic in ["load", "load_byte", "cmp"]:
        mode = get_operand_mode(raw[1])
    else:
        mode = get_operand_mode(raw[2])
    if mode in [0, 4, 5]:
        return 3
    elif mode == 1:
        return 4
    elif mode in [2, 3, 6]:
        return 5
    else:
        return 3


def encode_instruction(instr, labels):
    mnemonic = instr.mnemonic
    oper = instr.operands
    if mnemonic in ["halt", "reti", "int_enable", "int_disable"]:
        return [OPCODES[mnemonic]]
    if mnemonic in ["jmp", "jeq", "jne", "jlt", "jgt"] and len(oper) >= 1:
        mode, addr = parse_oper(oper[0].rstrip(","), labels)
        bytes_list = [OPCODES[mnemonic]]
        bytes_list.append(addr & 0xFF)
        bytes_list.append((addr >> 8) & 0xFF)
        return bytes_list
    bytes_list = [OPCODES[mnemonic]]
    parsed_op = []
    for op_str in oper:
        mode, value = parse_oper(op_str.rstrip(","), labels)
        parsed_op.append((mode, value))
    if mnemonic in ["load", "store", "load_byte", "store_byte", "cmp"]:
        if len(parsed_op) == 2:
            op1_mode, op1_val = parsed_op[0]
            op2_mode, op2_val = parsed_op[1]
            if mnemonic in ["load", "load_byte"]:
                rd = op1_val
                if op2_mode in [4, 5]:
                    rs = op2_val
                else:
                    rs = 0
                byte1 = (rd << 4) | rs
                if op2_mode == 0:
                    byte2 = (op2_mode << 4) | op2_val
                else:
                    byte2 = (op2_mode << 4) | 0
                bytes_list.append(byte1)
                bytes_list.append(byte2)
                if op2_mode == 1:
                    bytes_list.append(op2_val & 0xFF)
                elif op2_mode in [2, 3]:
                    bytes_list.append(op2_val & 0xFF)
                    bytes_list.append((op2_val >> 8) & 0xFF)
                elif op2_mode == 6:
                    addr = op2_val & 0xFFFF
                    bytes_list.append(addr & 0xFF)
                    bytes_list.append((addr >> 8) & 0xFF)
            elif mnemonic in ["store", "store_byte"]:
                rd = op2_val
                if op1_mode in [4, 5]:
                    rs = op1_val
                else:
                    rs = 0
                byte1 = (rd << 4) | rs
                if op1_mode == 6:
                    reg = (op1_val >> 16) & 0xF
                    byte2 = (op1_mode << 4) | reg
                else:
                    byte2 = (op1_mode << 4) | 0
                bytes_list.append(byte1)
                bytes_list.append(byte2)
                if op1_mode == 1:
                    bytes_list.append(op1_val & 0xFF)
                elif op1_mode in [2, 3]:
                    bytes_list.append(op1_val & 0xFF)
                    bytes_list.append((op1_val >> 8) & 0xFF)
                elif op1_mode == 6:
                    addr = op1_val & 0xFFFF
                    bytes_list.append(addr & 0xFF)
                    bytes_list.append((addr >> 8) & 0xFF)
            elif mnemonic == "cmp":
                rs = op1_val
                byte1 = (0 << 4) | rs
                byte2 = (op2_mode << 4) | op2_val
                bytes_list.append(byte1)
                bytes_list.append(byte2)
                if op2_mode == 1:
                    bytes_list.append(op2_val & 0xFF)
                elif op2_mode in [2, 3]:
                    bytes_list.append(op2_val & 0xFF)
                    bytes_list.append((op2_val >> 8) & 0xFF)
        return bytes_list
    if len(parsed_op) >= 3:
        rd = parsed_op[0][1]
        rs = parsed_op[1][1]
        mode = parsed_op[2][0]
        val = parsed_op[2][1]
        byte1 = (rd << 4) | rs
        bytes_list.append(byte1)
        if mode == 0:
            byte2 = (mode << 4) | val
            bytes_list.append(byte2)
        elif mode == 1:
            byte2 = (mode << 4) | 0
            bytes_list.append(byte2)
            bytes_list.append(val & 0xFF)
        elif mode == 2 or mode == 3:
            byte2 = (mode << 4) | 0
            bytes_list.append(byte2)
            bytes_list.append(val & 0xFF)
            bytes_list.append((val >> 8) & 0xFF)
        elif mode == 4:
            byte2 = (mode << 4) | val
            bytes_list.append(byte2)
        elif mode == 5:
            byte2 = (mode << 4) | (val & 0x0F)
            bytes_list.append(byte2)
        elif mode == 6:
            reg = (val >> 16) & 0xF
            addr = val & 0xFFFF
            byte2 = (mode << 4) | reg
            bytes_list.append(byte2)
            bytes_list.append(addr & 0xFF)
            bytes_list.append((addr >> 8) & 0xFF)
    return bytes_list


if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "program.asm"
    assemble(input_file, "program.bin", "program.lst")
