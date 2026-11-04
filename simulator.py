import sys


class Memory:
    def __init__(self, processor, size=0x10000):
        self.processor = processor
        self.data = bytearray(size)
        self.cache_block_size = 4
        self.cache_lines = 16
        self.cache_valid = [False] * self.cache_lines
        self.cache_tags = [0] * self.cache_lines
        self.cache_data = [bytearray(self.cache_block_size) for i in range(self.cache_lines)]
        self.hits = 0
        self.misses = 0

    def read_byte(self, address):
        offer = address % self.cache_block_size
        set_idx = (address // self.cache_block_size) % self.cache_lines
        tag = (address // self.cache_block_size) // self.cache_lines
        if self.cache_valid[set_idx] and self.cache_tags[set_idx] == tag:
            self.processor.cycles += 1
            self.hits += 1
            return self.cache_data[set_idx][offer]
        self.processor.cycles += 10
        self.misses += 1
        base_addr = address - offer
        for i in range(self.cache_block_size):
            if base_addr + i < len(self.data):
                self.cache_data[set_idx][i] = self.data[base_addr + i]
        self.cache_tags[set_idx] = tag
        self.cache_valid[set_idx] = True
        return self.cache_data[set_idx][offer]

    def read_word(self, address):
        b0 = self.read_byte(address)
        b1 = self.read_byte(address + 1)
        b2 = self.read_byte(address + 2)
        b3 = self.read_byte(address + 3)
        return (b3 << 24) | (b2 << 16) | (b1 << 8) | b0

    def write_byte(self, address, value):
        self.processor.cycles += 1
        self.data[address] = value & 0xFF
        offer = address % self.cache_block_size
        set_idx = (address // self.cache_block_size) % self.cache_lines
        tag = (address // self.cache_block_size) // self.cache_lines
        if self.cache_valid[set_idx] and self.cache_tags[set_idx] == tag:
            self.cache_data[set_idx][offer] = value & 0xFF
        if address == 0x84:
            self.processor.output_buffer.append(chr(value & 0xFF))
            self.processor.log(
                f"[Такт {self.processor.cycles}] ВЫВОД: символ '{chr(value & 0xFF)}' (ASCII {value & 0xFF})"
            )

    def write_word(self, address, value):
        self.write_byte(address, value)
        self.write_byte(address + 1, value >> 8)
        self.write_byte(address + 2, value >> 16)
        self.write_byte(address + 3, value >> 24)


class Processor:
    def __init__(self, log_filename="simulator.log"):
        self.memory = Memory(self)
        self.regs = [0] * 8

        self.pc = 0x0100  # счётчик команд
        self.epc = 0x0000  # то, куда мы будем кидать pc при прерываниях
        self.ir = []
        self.r_int = 0  # регистр прерывания
        self.ie = 0  # разрешение прерываний

        self.cycles = 0  # cчётчик тактов
        # флаги
        self.flag_z = 0
        self.flag_n = 0
        self.flag_c = 0
        self.flag_v = 0
        # для трэпа
        self.input_schedule = []
        self.output_buffer = []
        self.in_interrupt = False

        self.log_filename = log_filename
        self.log_file = open(self.log_filename, "w", encoding="utf-8")
        self.log("Начало работы процессора")

    def step(self):
        if self.check_interrupt():
            return True
        opcode = self.memory.read_byte(self.pc)
        mode = None
        self.ir = [opcode]
        # узнаем длину инструкции
        if opcode in [0x40, 0x41, 0x42, 0x43]:
            instr_len = 1
        else:
            self.ir.append(self.memory.read_byte(self.pc + 1))
            self.ir.append(self.memory.read_byte(self.pc + 2))
            mode = (self.ir[2] >> 4) & 0x0F
            if mode in [0, 4, 5]:
                instr_len = 3
            elif mode in [2, 3, 6]:
                instr_len = 5
            elif mode == 1:
                instr_len = 4
        for i in range(3, instr_len):
            self.ir.append(self.memory.read_byte(self.pc + i))
        ir_hex = " ".join(f"{b:02X}" for b in self.ir)
        self.log(f"[Такт {self.cycles}] FETCH: PC=0x{self.pc:04X}, IR=[{ir_hex}]")
        self.log(f"[Такт {self.cycles}] DECODE: опкод=0x{opcode:02X}")

        if opcode in [0x40, 0x41, 0x42, 0x43]:
            rd = rs = mode = rt = None
        else:
            rd = (self.ir[1] >> 4) & 0x0F
            rs = self.ir[1] & 0x0F
            rt = self.ir[2] & 0x0F
            self.log(f"[Такт {self.cycles}] DECODE: Rd=R{rd}, Rs=R{rs}, MODE={mode}, Rt=R{rt}")

        if opcode == 0x00:
            if mode in [0, 1, 2]:
                op2 = self.get_operand_value(mode, rt)
            else:
                addr = self.get_address(mode, rs, rt)  # адрес
                op2 = self.memory.read_word(addr)
            result = self.regs[rs] + op2
            self.update_flags(result, "add", self.regs[rs], op2)
            self.log(f"[Такт {self.cycles}] EXECUTE: add R{rd} = R{rs}({self.regs[rs]}) + {op2} = {result}")
            self.write_register(rd, result)
            self.pc += instr_len
            self.dump_state()
            return True

        elif opcode == 0x01:
            if mode in [0, 1, 2]:
                op2 = self.get_operand_value(mode, rt)
            else:
                addr = self.get_address(mode, rs, rt)  # адрес
                op2 = self.memory.read_word(addr)
            result = self.regs[rs] - op2
            self.update_flags(result, "sub", self.regs[rs], op2)
            self.log(f"[Такт {self.cycles}] EXECUTE: sub R{rd} = R{rs}({self.regs[rs]}) - {op2} = {result}")
            self.write_register(rd, result)
            self.pc += instr_len
            return True
        elif opcode == 0x02:
            if mode not in [0, 1, 2]:
                self.log(f"[Такт {self.cycles}] EXECUTE: adc не поддерживает MODE {mode}")
                return False
            op2 = self.get_operand_value(mode, rt)
            result = self.regs[rs] + op2 + self.flag_c
            self.log(
                f"[Такт {self.cycles}] EXECUTE: adc R{rd} = R{rs}({self.regs[rs]}) + {op2} + C{self.flag_c} = {result}"
            )
            self.update_flags(result, "adc", self.regs[rs], op2, self.flag_c)
            self.write_register(rd, result)
            self.pc += instr_len
            self.dump_state()
            return True

        elif opcode == 0x03:
            if mode not in [0, 1]:
                self.log(f"[Такт {self.cycles}] EXECUTE: mul поддерживает только MODE 0, 1")
                return False
            op2 = self.get_operand_value(mode, rt)
            result = (self.regs[rs] * op2) & 0xFFFFFFFF
            self.log(f"[Такт {self.cycles}] EXECUTE: mul R{rd} = R{rs} * {op2} = {result}")
            self.update_flags(result, "logic", self.regs[rs], op2)
            self.write_register(rd, result)
            self.pc += instr_len
            self.dump_state()
            return True

        elif opcode == 0x04:
            if mode not in [0, 1]:
                self.log(f"[Такт {self.cycles}] EXECUTE: div поддерживает только MODE 0, 1")
                return False
            op2 = self.get_operand_value(mode, rt)
            if op2 == 0:
                self.log(f"[Такт {self.cycles}] EXECUTE: Division by zero!")
                return False
            a = self.regs[rs]
            if a > 0x7FFFFFFF:
                a -= 0x100000000
            if op2 > 0x7FFFFFFF:
                op2 -= 0x100000000
            res = a // op2
            result = res & 0xFFFFFFFF
            self.log(f"[Такт {self.cycles}] EXECUTE: div R{rd} = R{rs} // {op2} = {result}")
            self.update_flags(result, "logic", self.regs[rs], op2)
            self.write_register(rd, result)
            self.pc += instr_len
            self.dump_state()
            return True

        elif opcode == 0x05:
            if mode not in [0, 1]:
                self.log(f"[Такт {self.cycles}] EXECUTE: mod поддерживает только MODE 0, 1")
                return False
            op2 = self.get_operand_value(mode, rt)
            if op2 == 0:
                self.log(f"[Такт {self.cycles}] EXECUTE: Division by zero!")
                return False
            a = self.regs[rs]
            if a > 0x7FFFFFFF:
                a -= 0x100000000
            if op2 > 0x7FFFFFFF:
                op2 -= 0x100000000
            res = a % op2
            result = res & 0xFFFFFFFF
            self.log(f"[Такт {self.cycles}] EXECUTE: mod R{rd} = R{rs} // {op2} = {result}")
            self.update_flags(result, "logic", self.regs[rs], op2)
            self.write_register(rd, result)
            self.pc += instr_len
            self.dump_state()
            return True

        elif opcode == 0x06:
            if mode in [0, 1, 2]:
                op2 = self.get_operand_value(mode, rt)
            else:
                addr = self.get_address(mode, rs, rt)
                op2 = self.memory.read_word(addr)
            result = self.regs[rs] & op2
            self.log(f"[Такт {self.cycles}] EXECUTE: and R{rd} = R{rs}({self.regs[rs]}) & {op2} = {result}")
            self.update_flags(result, "and", self.regs[rs], op2)
            self.write_register(rd, result)
            self.pc += instr_len
            self.dump_state()
            return True

        elif opcode == 0x07:
            if mode in [0, 1, 2]:
                op2 = self.get_operand_value(mode, rt)
            else:
                addr = self.get_address(mode, rs, rt)
                op2 = self.memory.read_word(addr)
            result = self.regs[rs] | op2
            self.log(f"[Такт {self.cycles}] EXECUTE: or R{rd} = R{rs}({self.regs[rs]}) | {op2} = {result}")
            self.update_flags(result, "or", self.regs[rs], op2)
            self.write_register(rd, result)
            self.pc += instr_len
            self.dump_state()
            return True

        elif opcode == 0x08:
            if mode != 1:
                self.log(f"[Такт {self.cycles}] EXECUTE: lsl поддерживает только MODE 1")
                return False
            op2 = self.get_operand_value(mode, rt)
            if op2 < 0:
                self.log(f"[Такт {self.cycles}] EXECUTE: lsl поддерживает только положительные сдвиги")
                return False
            result = (self.regs[rs] << op2) & 0xFFFFFFFF
            self.log(f"[Такт {self.cycles}] EXECUTE: lsl R{rd} = R{rs} << {op2} = {result}")
            self.update_flags(result, "logic", self.regs[rs], op2)
            self.write_register(rd, result)
            self.pc += instr_len
            self.dump_state()
            return True

        elif opcode == 0x09:
            if mode != 1:
                self.log(f"[Такт {self.cycles}] EXECUTE: lsr поддерживает только MODE 1")
                return False
            op2 = self.get_operand_value(mode, rt)
            if op2 < 0:
                self.log(f"[Такт {self.cycles}] EXECUTE: lsr поддерживает только положительные сдвиги")
                return False
            result = (self.regs[rs] >> op2) & 0xFFFFFFFF
            self.log(f"[Такт {self.cycles}] EXECUTE: lsr R{rd} = R{rs} >> {op2} = {result}")
            self.update_flags(result, "logic", self.regs[rs], op2)
            self.write_register(rd, result)
            self.pc += instr_len
            self.dump_state()
            return True

        elif opcode == 0x10:
            if mode in [0, 1, 2]:
                op2 = self.get_operand_value(mode, rt)
                self.log(f"[Такт {self.cycles}] EXECUTE: load (mov) R{rd} = R{rt}({op2})")
                self.write_register(rd, op2)
            else:
                addr = self.get_address(mode, rs, rt)
                op2 = self.memory.read_word(addr)
                self.log(f"[Такт {self.cycles}] EXECUTE: load R{rd} = [{addr:04X}] = {op2}")
                self.write_register(rd, op2)
            self.pc += instr_len
            self.dump_state()
            return True

        elif opcode == 0x11:
            addr = self.get_address(mode, rs, rt)
            value = self.regs[rd]
            self.memory.write_word(addr, value)
            self.log(f"[Такт {self.cycles}] EXECUTE: store R{rd} {addr}")
            self.pc += instr_len
            self.dump_state()
            return True

        elif opcode == 0x12:
            addr = self.get_address(mode, rs, rt)
            op2 = self.memory.read_byte(addr)
            self.log(f"[Такт {self.cycles}] EXECUTE: load_byte R{rd} {op2}")
            self.write_register(rd, op2)
            self.pc += instr_len
            self.dump_state()
            return True

        elif opcode == 0x13:
            addr = self.get_address(mode, rs, rt)
            value = self.regs[rd]
            self.memory.write_byte(addr, value)
            self.log(f"[Такт {self.cycles}] EXECUTE: store_byte R{rd} {addr}")
            self.pc += instr_len
            self.dump_state()
            return True

        elif opcode == 0x20:
            if mode in [0, 1, 2]:
                op2 = self.get_operand_value(mode, rt)
            else:
                addr = self.get_address(mode, rs, rt)
                op2 = self.memory.read_word(addr)
            a = self.regs[rs]
            result = a - op2
            self.log(f"[Такт {self.cycles}] EXECUTE: CMP R{rs}({a}) - {op2} = {result}")
            self.update_flags(result, "cmp", a, op2)
            self.pc += instr_len
            self.dump_state()
            return True
        elif opcode in [0x30, 0x31, 0x32, 0x33, 0x34]:
            addr = self.ir[1] | (self.ir[2] << 8)
            jump = False
            if opcode == 0x30:
                jump = True
            if opcode == 0x31:
                jump = self.flag_z == 1
            elif opcode == 0x32:  # jne если Z==0
                jump = self.flag_z == 0
            elif opcode == 0x33:  # jlt если N != V
                jump = self.flag_n != self.flag_v
            elif opcode == 0x34:  # jgt если Z==0 и N == V
                jump = (self.flag_z == 0) and (self.flag_n == self.flag_v)
            if jump:
                self.log(f"[Такт {self.cycles}] EXECUTE: jump to 0x{addr:04X}")
                self.pc = addr
            else:
                self.log(f"[Такт {self.cycles}] EXECUTE: no jump, continue to 0x{self.pc + instr_len:04X}")
                self.pc += instr_len
            self.dump_state()
            return True

        elif opcode == 0x40:
            self.ie = 1
            self.log(f"[Такт {self.cycles}] EXECUTE: int_enable (прерывания разрешены)")
            self.pc += instr_len
            self.dump_state()
            return True

        elif opcode == 0x41:
            self.ie = 0
            self.log(f"[Такт {self.cycles}] EXECUTE: int_disable (прерывания запрещены)")
            self.pc += instr_len
            self.dump_state()
            return True

        elif opcode == 0x42:
            self.log(f"[Такт {self.cycles}] EXECUTE: reti (возврат на 0x{self.epc:04X})")
            self.pc = self.epc
            self.ie = 1
            self.in_interrupt = False
            self.dump_state()
            return True

        elif opcode == 0x43:
            self.log(f"[Такт {self.cycles}] EXECUTE: halt - остановка процессора")
            return False
        else:
            self.log(f"[Такт {self.cycles}] EXECUTE: команда с опкодом 0x{opcode:02X} пока не реализована")
            return False

    def run(self):
        self.log("Процессор запущен")
        limit = 50000
        while self.step():
            if self.cycles > limit:
                self.log(f"лимит {limit} тактов превышен")
                break
        self.log(f"Stop. Всего тактов: {self.cycles}")
        self.close()

    def write_register(self, rd, result):
        if rd == 15:
            self.log(f"[Такт {self.cycles}] WRITEBACK: попытка записи в R_INT запрещена")
        elif rd < 8:
            result_32 = result & 0xFFFFFFFF
            self.regs[rd] = result_32
            self.log(f"[Такт {self.cycles}] WRITEBACK: R{rd} = {result_32}")
        else:
            self.log(f"[Такт {self.cycles}] WRITEBACK: регистр {rd} зарезервирован")

    def update_flags(self, result, operation=None, a=None, b=None, carry=0):
        result_32 = result & 0xFFFFFFFF
        self.flag_n = (result_32 >> 31) & 1
        if result_32 == 0:
            self.flag_z = 1
        else:
            self.flag_z = 0
        if a is not None and b is not None:
            a_32 = a & 0xFFFFFFFF
            b_32 = b & 0xFFFFFFFF
            sign_a = (a_32 >> 31) & 1
            sign_b = (b_32 >> 31) & 1
            sign_r = (result_32 >> 31) & 1
            if operation in ["sub", "cmp"]:
                if a_32 < b_32:
                    self.flag_c = 1
                else:
                    self.flag_c = 0
                if (sign_a != sign_b) and (sign_r != sign_a):
                    self.flag_v = 1
                else:
                    self.flag_v = 0
            elif operation in ["add", "adc"]:
                if (a_32 + b_32 + carry) > 0xFFFFFFFF:
                    self.flag_c = 1
                else:
                    self.flag_c = 0
                if (sign_a == sign_b) and (sign_r != sign_a):
                    self.flag_v = 1
                else:
                    self.flag_v = 0
            elif operation in ["and", "or"] or operation == "logic":
                self.flag_c = 0
                self.flag_v = 0

    def check_interrupt(self):
        if self.in_interrupt:
            if len(self.input_schedule) > 0 and self.cycles >= self.input_schedule[0][0]:
                self.log(f"[Такт {self.cycles}] Прерывание в прерывании")
            return False
        if self.ie == 1 and len(self.input_schedule) > 0:
            if self.cycles >= self.input_schedule[0][0]:
                tick, value = self.input_schedule.pop(0)
                self.log(f"[Такт {self.cycles}] - прерывание (trap)")
                self.log(f"Сохраняем PC=0x{self.pc:04X} в EPC")
                self.log(f"Записываем значение {value} в R_INT")
                self.epc = self.pc
                self.r_int = value
                self.ie = 0
                self.pc = 0x0
                self.in_interrupt = True
                return True
        return False

    def get_operand_value(self, mode, rt):
        if mode == 0:
            if rt == 15:
                return self.r_int
            return self.regs[rt]

        elif mode == 1:
            imm = self.ir[3]
            if imm >= 0x80:
                imm = imm - 0x100
            return imm

        elif mode == 2:
            imm = (self.ir[4] << 8) | self.ir[3]
            if imm >= 0x8000:
                imm = imm - 0x10000
            return imm

        else:
            return 0

    def get_address(self, mode, rs, rt):
        if mode == 3:  # прямой адрес
            return (self.ir[4] << 8) | self.ir[3]
        elif mode == 4:  # косвенный
            return self.regs[rs]
        elif mode == 5:  # +индекс [Rs + Rt]
            return self.regs[rs] + self.regs[rt]
        elif mode == 6:  # константа+индекс [addr16 + Rt]
            return ((self.ir[4] << 8) | self.ir[3]) + self.regs[rt]

    def log(self, message):
        self.log_file.write(message + "\n")

    def dump_state(self):
        regs_str = ", ".join([f"R{i}={self.regs[i]:08X}" for i in range(8)])
        flags_str = f"z={self.flag_z} n={self.flag_n} c={self.flag_c} v={self.flag_v}"
        ie_str = f"IE={self.ie}"
        self.log(f"[state] {regs_str} | flags: {flags_str} | {ie_str}")

    def close(self):
        self.log("~" * 60)
        self.log("The end.")
        self.log("~" * 60)
        self.log_file.close()

    def load_program(self, filename, base_addr=0x0000):
        with open(filename, "rb") as f:
            program_bytes = f.read()
        end_addr = base_addr + len(program_bytes)
        if end_addr > len(self.memory.data):
            raise ValueError(f"Ошибка: программа {len(program_bytes)} байт не помещается в память...")
        self.memory.data[base_addr:end_addr] = program_bytes
        self.log(f"Загружена программа из {filename}")

    def load_schedule(self, input_file):
        schedule = []
        with open(input_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) == 2:
                    tick = int(parts[0])
                    value = int(parts[1])
                    schedule.append((tick, value))
        return schedule


if __name__ == "__main__":
    if len(sys.argv) > 1:
        bin_file = sys.argv[1]
    else:
        bin_file = "program.bin"
    cpu = Processor(log_filename="simulator.log")
    try:
        cpu.load_program(bin_file, base_addr=0x0000)
    except FileNotFoundError:
        print(f"Ошибка: файл {bin_file} не найден. Сначала запусти транслятор и ассемблер!")
        sys.exit(1)
    except ValueError as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

    if len(sys.argv) > 2:
        schedule_file = sys.argv[2]
        cpu.input_schedule = cpu.load_schedule(schedule_file)
    else:
        cpu.input_schedule = []
    print("Выполнение программы...")
    cpu.run()
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ:")
    print(f"Всего тактов: {cpu.cycles}")
    print(f"Кэш: HIT={cpu.memory.hits}, MISS={cpu.memory.misses}")
    if cpu.output_buffer:
        print(f"Вывод программы: '{''.join(cpu.output_buffer)}'")
    else:
        print("Вывод программы: (пусто)")
    codes = [ord(c) for c in cpu.output_buffer]
    print(f"Вывод (коды байтов): {codes}")
    print("=" * 60)
    print("Подробный журнал сохранен в simulator.log")
