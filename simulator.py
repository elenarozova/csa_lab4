class Processor:
    def __init__(self):
        self.memory = bytearray(0x10000)
        self.regs = [0]*8

        self.pc = 0x0100    #счётчик команд
        self.epc = 0x0000   #то, куда мы будем кидать pc при прерываниях
        self.ir = []
        self.r_int = 0  #регистр прерывания
        self.ie = 0     #разрешение прерываний

        self.cycles = 0 #cчётчик тактов
        #флаги
        self.flag_z = 0  
        self.flag_n = 0
        self.flag_c = 0
        self.flag_v = 0
        #для трэпа
        self.input_schedule = [] 
        self.output_buffer = [] 
        self.in_interrupt = False

    def read_byte(self, address):
        # В будущем здесь будет логика кэша (1 или 10 тактов)
        self.cycles += 1
        return self.memory[address]
    
    def read_word(self, address):
        b0 = self.read_byte(address)
        b1 = self.read_byte(address+1)
        b2 = self.read_byte(address+2)
        b3 = self.read_byte(address+3)
        return (b3<<24) |(b2<<16) |(b1<<8) | b0
    
    def write_byte(self, address, value):
        self.cycles += 1
        self.memory[address] = value & 0xFF

    def write_word(self, address, value):
        self.write_byte(address, value)
        self.write_byte(address+1, value>>8)
        self.write_byte(address+2, value>>16)
        self.write_byte(address+3, value>>24)
        

        

    def step(self):
        opcode = self.read_byte(self.pc)
        mode = None
        self.ir = [opcode]
        #узнаем длину инструкции
        if opcode in [0x40, 0x41, 0x42, 0x43]:
            instr_len = 1
        else:
            self.ir.append(self.read_byte(self.pc + 1))
            self.ir.append(self.read_byte(self.pc + 2))
            mode = (self.ir[2] >> 4) & 0x0F
            if (mode in [0, 4, 5]):
                instr_len = 3
            elif mode in [2, 3,6]:
                instr_len = 5
            elif mode==1:
                instr_len = 4
        for i in range(3, instr_len):
            self.ir.append(self.read_byte(self.pc + i))
        ir_hex = ' '.join(f'{b:02X}' for b in self.ir)
        print(f"[Такт {self.cycles}] FETCH: PC=0x{self.pc:04X}, IR=[{ir_hex}]")
        print(f"[Такт {self.cycles}] DECODE: опкод=0x{opcode:02X}")

        if opcode in [0x40, 0x41, 0x42, 0x43]: 
            rd = rs = mode = rt = None
            imm = None
        else:
            rd = (self.ir[1] >> 4) & 0x0F
            rs = self.ir[1] & 0x0F
            rt = self.ir[2] & 0x0F
            imm = None
            print(f"[Такт {self.cycles}] DECODE: Rd=R{rd}, Rs=R{rs}, MODE={mode}, Rt=R{rt}")

        if opcode == 0x43:
            print(f"[Такт {self.cycles}] EXECUTE: halt - остановка процессора")
            return False
        elif opcode == 0x00:
            if mode in [0, 1, 2]:
                op2 = self.get_operand_value(mode, rt)
            else:
                addr = self.get_address(mode, rs, rt)  # адрес
                op2 = self.read_word(addr)
            result = self.regs[rs] + op2
            self.update_flags(result,"add",self.regs[rs], op2 )
            print(f"[Такт {self.cycles}] EXECUTE: add R{rd} = R{rs}({self.regs[rs]}) + {op2} = {result}")
            self.write_register(rd, result)
            self.pc += instr_len
            return True
        elif opcode == 0x01:
            if mode in [0, 1, 2]:
                op2 = self.get_operand_value(mode, rt)
            else:
                addr = self.get_address(mode, rs, rt)  # адрес
                op2 = self.read_word(addr)
            result = self.regs[rs] - op2
            self.update_flags(result, "sub", self.regs[rs], op2)
            print(f"[Такт {self.cycles}] EXECUTE: sub R{rd} = R{rs}({self.regs[rs]}) - {op2} = {result}")
            self.write_register(rd, result)
            self.pc += instr_len
            return True
        elif opcode == 0x02:
            if mode not in [0, 1, 2]:
                print(f"[Такт {self.cycles}] EXECUTE: adc не поддерживает MODE {mode}")
                return False
            op2 = self.get_operand_value(mode, rt)
            result = self.regs[rs] + op2 + self.flag_c
            print(f"[Такт {self.cycles}] EXECUTE: adc R{rd} = R{rs}({self.regs[rs]}) + {op2} + C{self.flag_c} = {result}")
            self.update_flags(result,"adc",self.regs[rs], op2, self.flag_c)
            self.write_register(rd, result)
            self.pc += instr_len
            return True

        elif opcode == 0x03:
            if mode not in [0, 1]:
                print(f"[Такт {self.cycles}] EXECUTE: mul поддерживает только MODE 0, 1")
                return False
            op2 = self.get_operand_value(mode, rt)
            result = (self.regs[rs] * op2) & 0xFFFFFFFF
            print(f"[Такт {self.cycles}] EXECUTE: mul R{rd} = R{rs} * {op2} = {result}")
            self.update_flags(result, "logic", self.regs[rs], op2)
            self.write_register(rd, result)
            self.pc += instr_len
            return True
        
        elif opcode == 0x04:  
            if mode not in [0, 1]:
                print(f"[Такт {self.cycles}] EXECUTE: div поддерживает только MODE 0, 1")
                return False
            op2 = self.get_operand_value(mode, rt)
            if op2 == 0:
                print(f"[Такт {self.cycles}] EXECUTE: Division by zero!")
                return False
            a = self.regs[rs]
            if a > 0x7FFFFFFF: a -= 0x100000000
            if op2 > 0x7FFFFFFF: op2 -= 0x100000000
            res = a // op2
            result = res & 0xFFFFFFFF
            print(f"[Такт {self.cycles}] EXECUTE: div R{rd} = R{rs} // {op2} = {result}")
            self.update_flags(result, "logic", self.regs[rs], op2)
            self.write_register(rd, result)
            self.pc += instr_len
            return True

        elif opcode == 0x05:  
                    if mode not in [0, 1]:
                        print(f"[Такт {self.cycles}] EXECUTE: mod поддерживает только MODE 0, 1")
                        return False
                    op2 = self.get_operand_value(mode, rt)
                    if op2 == 0:
                        print(f"[Такт {self.cycles}] EXECUTE: Division by zero!")
                        return False
                    a = self.regs[rs]
                    if a > 0x7FFFFFFF: a -= 0x100000000
                    if op2 > 0x7FFFFFFF: op2 -= 0x100000000
                    res = a % op2
                    result = res & 0xFFFFFFFF
                    print(f"[Такт {self.cycles}] EXECUTE: mod R{rd} = R{rs} // {op2} = {result}")
                    self.update_flags(result, "logic", self.regs[rs], op2)
                    self.write_register(rd, result)
                    self.pc += instr_len
                    return True
        
        elif opcode == 0x06:  
            if mode in [0, 1, 2]:
                op2 = self.get_operand_value(mode, rt)
            else:
                addr = self.get_address(mode, rs, rt)
                op2 = self.read_word(addr)
            result = self.regs[rs] & op2
            print(f"[Такт {self.cycles}] EXECUTE: and R{rd} = R{rs}({self.regs[rs]}) & {op2} = {result}")
            self.update_flags(result, "and", self.regs[rs], op2)
            self.write_register(rd, result)
            self.pc += instr_len
            return True

        elif opcode == 0x07:  
            if mode in [0, 1, 2]:
                op2 = self.get_operand_value(mode, rt)
            else:
                addr = self.get_address(mode, rs, rt)
                op2 = self.read_word(addr)
            result = self.regs[rs] | op2
            print(f"[Такт {self.cycles}] EXECUTE: or R{rd} = R{rs}({self.regs[rs]}) | {op2} = {result}")
            self.update_flags(result, "or", self.regs[rs], op2)
            self.write_register(rd, result)
            self.pc += instr_len
            return True
        
        elif opcode == 0x08: 
            if mode != 1:
                print(f"[Такт {self.cycles}] EXECUTE: lsl поддерживает только MODE 1")
                return False
            op2 = self.get_operand_value(mode, rt)
            if op2<0:
                print(f"[Такт {self.cycles}] EXECUTE: lsl поддерживает только положительные сдвиги")
                return False
            result = (self.regs[rs] << op2) & 0xFFFFFFFF
            print(f"[Такт {self.cycles}] EXECUTE: lsl R{rd} = R{rs} << {op2} = {result}")
            self.update_flags(result, "logic", self.regs[rs], op2)
            self.write_register(rd, result)
            self.pc += instr_len
            return True

        elif opcode == 0x09: 
            if mode != 1:
                print(f"[Такт {self.cycles}] EXECUTE: lsr поддерживает только MODE 1")
                return False
            op2 = self.get_operand_value(mode, rt)
            if op2<0:
                print(f"[Такт {self.cycles}] EXECUTE: lsr поддерживает только положительные сдвиги")
                return False
            result = (self.regs[rs] >> op2) & 0xFFFFFFFF
            print(f"[Такт {self.cycles}] EXECUTE: lsr R{rd} = R{rs} >> {op2} = {result}")
            self.update_flags(result, "logic", self.regs[rs], op2)
            self.write_register(rd, result)
            self.pc += instr_len
            return True
        
        elif opcode==0x10:
            addr = self.get_address(mode, rs, rt)
            op2 = self.read_word(addr)
            print(f"[Такт {self.cycles}] EXECUTE: load R{rd} {op2}")
            self.write_register(rd, op2)
            self.pc += instr_len
            return True
        elif opcode==0x11:
            addr = self.get_address(mode, rs, rt)
            value = self.regs[rd]
            self.write_word(addr, value)
            print(f"[Такт {self.cycles}] EXECUTE: store R{rd} {addr}")
            self.pc += instr_len
            return True
        elif opcode==0x12:
            addr = self.get_address(mode, rs, rt)
            op2 = self.read_byte(addr)
            print(f"[Такт {self.cycles}] EXECUTE: load_byte R{rd} {op2}")
            self.write_register(rd, op2)
            self.pc += instr_len
            return True
        elif opcode==0x13:
            addr = self.get_address(mode, rs, rt)
            value = self.regs[rd]
            self.write_byte(addr, value)
            print(f"[Такт {self.cycles}] EXECUTE: store_byte R{rd} {addr}")
            self.pc += instr_len
            return True

        elif opcode == 0x20:
            if mode in [0, 1, 2]:
                op2 = self.get_operand_value(mode, rt)
            else:
                addr = self.get_address(mode, rs, rt)
                op2 = self.read_word(addr)
            a = self.regs[rs]
            result = a - op2
            print(f"[Такт {self.cycles}] EXECUTE: CMP R{rs}({a}) - {op2} = {result}")
            self.update_flags(result,'cmp', a, op2)
            self.pc += instr_len
            return True
        elif opcode in [0x30,0x31, 0x32, 0x33,0x34]:
            addr = self.ir[1] | (self.ir[2] << 8)
            jump = False
            if opcode == 0x30:
                jump=True
            if opcode == 0x31:
                jump = self.flag_z == 1
            elif opcode == 0x32:  # jne — если Z=0
                jump = self.flag_z == 0
            elif opcode == 0x33:  # jlt — если N != V
                jump = self.flag_n != self.flag_v
            elif opcode == 0x34:  # jgt — если Z=0 и N == V
                jump = (self.flag_z == 0) and (self.flag_n == self.flag_v)
            if jump:
                print(f"[Такт {self.cycles}] EXECUTE: jump to 0x{addr:04X}")
                self.pc = addr
            else:
                print(f"[Такт {self.cycles}] EXECUTE: no jump, continue to 0x{self.pc + instr_len:04X}")
                self.pc += instr_len
            return True
    

        else:
            print(f"[Такт {self.cycles}] EXECUTE: команда с опкодом 0x{opcode:02X} пока не реализована")
            return False
    


    
    def run(self):
        print("=" * 60)
        print("ЗАПУСК ПРОЦЕССОРА")
        print("=" * 60)
        
        while self.step():
            pass
        
        print("=" * 60)
        print(f"ПРОЦЕССОР ОСТАНОВЛЕН. Всего тактов: {self.cycles}")
        print("=" * 60)

    def write_register(self, rd, result):
        if rd == 15:
            print(f"[Такт {self.cycles}] WRITEBACK: попытка записи в R_INT запрещена")
        elif rd < 8:
            # Маскируем до 32 бит (беззнаковое представление)
            result_32 = result & 0xFFFFFFFF
            self.regs[rd] = result_32
            print(f"[Такт {self.cycles}] WRITEBACK: R{rd} = {result_32}")
        else:
            print(f"[Такт {self.cycles}] WRITEBACK: регистр {rd} зарезервирован")

    def update_flags(self, result, operation=None, a=None, b=None, carry = 0):
        result_32 = result & 0xFFFFFFFF
        self.flag_n = (result_32 >> 31) & 1
        if result_32==0: self.flag_z = 1
        else: self.flag_z = 0
        if a is not None and b is not None:
            a_32 = a & 0xFFFFFFFF
            b_32 = b & 0xFFFFFFFF
            sign_a = (a_32 >> 31) & 1
            sign_b = (b_32 >> 31) & 1
            sign_r = (result_32 >> 31) & 1
            if operation in ['sub', 'cmp']:
                if a_32 < b_32: self.flag_c = 1
                else: self.flag_c = 0
                if ((sign_a != sign_b) and (sign_r != sign_a)): self.flag_v = 1
                else: self.flag_v = 0
            elif operation in ['add', 'adc']:
                if (a_32 + b_32 + carry) > 0xFFFFFFFF: 
                    self.flag_c = 1
                else: self.flag_c = 0
                if ((sign_a == sign_b) and (sign_r != sign_a)): self.flag_v = 1
                else: self.flag_v = 0
            elif operation in ['and', 'or']:
                self.flag_c = 0
                self.flag_v = 0
            elif operation == 'logic': 
                self.flag_c = 0
                self.flag_v = 0
            




    def get_operand_value(self, mode, rt):
        if mode == 0:
            op2 = self.regs[rt]
        elif mode == 1:
            imm = self.ir[3]
            if imm >= 0x80:     #Константа 8 бит (знаковая)
                imm = imm - 0x100
            op2 = imm
        elif mode == 2:  
            imm = (self.ir[4] << 8) | self.ir[3]
            if imm >= 0x8000: #Константа 16 бит (знаковая)
                imm = imm - 0x10000
            op2 = imm
        else:
            return False
        return op2

    def get_address(self,mode, rs, rt):
        if  mode == 3:    # Прямой адрес [addr16]
            return (self.ir[4] << 8) | self.ir[3]
        elif mode == 4:     # Косвенный [Rs]
            return  self.regs[rs]
        elif mode == 5:     # База+индекс [Rs + Rt]
            return self.regs[rs] + self.regs[rt]
        elif mode == 6:     # Константа+индекс [addr16 + Rt]
            return ((self.ir[4] << 8) | self.ir[3])  + self.regs[rt]


if __name__ == "__main__":
    print("=" * 60)
    print("ТЕСТ 1: MUL (умножение)")
    print("=" * 60)
    cpu = Processor()
    
    # mul r0, r1, r2 (3 байта)
    # 12345 * 6789 = 83810205
    cpu.memory[0x0100] = 0x03  # опкод mul
    cpu.memory[0x0101] = 0x01  # Rd=0, Rs=1
    cpu.memory[0x0102] = 0x02  # MODE=0, Rt=2
    cpu.memory[0x0103] = 0x43  # halt
    
    cpu.regs[1] = 12345
    cpu.regs[2] = 6789
    
    cpu.run()
    
    print(f"\nПРОВЕРКА MUL:")
    print(f"  R0 = {cpu.regs[0]} (ожидалось 83810205)")
    print(f"  flag_z = {cpu.flag_z} (ожидалось 0)")
    print(f"  flag_n = {cpu.flag_n} (ожидалось 0)")
    assert cpu.regs[0] == 83810205, "MUL failed!"
    print("  ✓ MUL прошёл успешно\n")
    
    print("=" * 60)
    print("ТЕСТ 2: DIV (деление)")
    print("=" * 60)
    cpu = Processor()
    
    # div r0, r1, r2 (3 байта)
    # 100 / 7 = 14 (целочисленное деление)
    cpu.memory[0x0100] = 0x04  # опкод div
    cpu.memory[0x0101] = 0x01  # Rd=0, Rs=1
    cpu.memory[0x0102] = 0x02  # MODE=0, Rt=2
    cpu.memory[0x0103] = 0x43  # halt
    
    cpu.regs[1] = 100
    cpu.regs[2] = 7
    
    cpu.run()
    
    print(f"\nПРОВЕРКА DIV:")
    print(f"  R0 = {cpu.regs[0]} (ожидалось 14)")
    print(f"  flag_z = {cpu.flag_z} (ожидалось 0)")
    assert cpu.regs[0] == 14, "DIV failed!"
    print("  ✓ DIV прошёл успешно\n")
    
    print("=" * 60)
    print("ТЕСТ 3: MOD (остаток)")
    print("=" * 60)
    cpu = Processor()
    
    # mod r0, r1, r2 (3 байта)
    # 100 % 7 = 2 (остаток)
    cpu.memory[0x0100] = 0x05  # опкод mod
    cpu.memory[0x0101] = 0x01  # Rd=0, Rs=1
    cpu.memory[0x0102] = 0x02  # MODE=0, Rt=2
    cpu.memory[0x0103] = 0x43  # halt
    
    cpu.regs[1] = 100
    cpu.regs[2] = 7
    
    cpu.run()
    
    print(f"\nПРОВЕРКА MOD:")
    print(f"  R0 = {cpu.regs[0]} (ожидалось 2)")
    assert cpu.regs[0] == 2, "MOD failed!"
    print("  ✓ MOD прошёл успешно\n")
    
    print("=" * 60)
    print("ТЕСТ 4: LOAD_BYTE / STORE_BYTE")
    print("=" * 60)
    cpu = Processor()
    
    # store_byte [0x3000], r1 (3 байта)
    # Сохраняем младший байт из R1 (0xAB) по адресу 0x3000
    cpu.memory[0x0100] = 0x13  # опкод store_byte
    cpu.memory[0x0101] = 0x10  # Rd=1 (что сохраняем), Rs не исп.
    cpu.memory[0x0102] = 0x30  # MODE=3 (прямой адрес), Rt не исп.
    cpu.memory[0x0103] = 0x00  # адрес 0x3000 (little-endian)
    cpu.memory[0x0104] = 0x30
    
    # load_byte r0, [0x3000] (3 байта)
    # Загружаем байт из 0x3000 в R0
    cpu.memory[0x0105] = 0x12  # опкод load_byte
    cpu.memory[0x0106] = 0x00  # Rd=0, Rs не исп.
    cpu.memory[0x0107] = 0x30  # MODE=3, Rt не исп.
    cpu.memory[0x0108] = 0x00  # адрес 0x3000
    cpu.memory[0x0109] = 0x30
    
    # halt
    cpu.memory[0x010A] = 0x43
    
    # R1 = 0x12345678, младший байт = 0x78 = 120
    cpu.regs[1] = 0x12345678
    
    cpu.run()
    
    print(f"\nПРОВЕРКА LOAD_BYTE / STORE_BYTE:")
    print(f"  Память[0x3000] = {cpu.memory[0x3000]:02X} (ожидалось 78)")
    print(f"  R0 = {cpu.regs[0]} (ожидалось 120)")
    assert cpu.memory[0x3000] == 0x78, "STORE_BYTE failed!"
    assert cpu.regs[0] == 120, "LOAD_BYTE failed!"
    print("  ✓ LOAD_BYTE / STORE_BYTE прошли успешно\n")
    
    print("=" * 60)
    print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ! 🎉")
    print("=" * 60)