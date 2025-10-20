
# Convert TAC list into simple  pseudo-assembly...

class MachineGenerator:
    def __init__(self, num_registers=4):
        self.num_registers = num_registers
        self.reg_map = {}     # operand -> register name...
        self.reg_in_use = []  # list of operands in registers order...
        self.asm = []

    def get_reg(self, operand):
        # if oper already in register, return it...
        if operand in self.reg_map:
            return self.reg_map[operand]

        if len(self.reg_in_use) < self.num_registers:
            r = f"R{len(self.reg_in_use)+1}"
            self.reg_map[operand] = r
            self.reg_in_use.append(operand)
            if self.is_literal(operand):
                self.asm.append(f"LOADI {r}, {operand}")
            else:
                self.asm.append(f"LOAD {r}, {operand}")
            return r

        
        spilled = self.reg_in_use.pop(0)
        r = self.reg_map.pop(spilled)
        self.asm.append(f"STORE {r}, {spilled}")
        self.reg_map[operand] = r
        self.reg_in_use.append(operand)
        if self.is_literal(operand):
            self.asm.append(f"LOADI {r}, {operand}")
        else:
            self.asm.append(f"LOAD {r}, {operand}")
        return r

    def is_literal(self, op):
        if op.startswith("'") and op.endswith("'"):
            return True
        try:
            float(op)
            return True
        except:
            return False

    def free_reg_of(self, operand):
        if operand in self.reg_map:
            r = self.reg_map.pop(operand)
            if operand in self.reg_in_use:
                self.reg_in_use.remove(operand)
            return r
        return None

    def binop(self, dest, a, op, b):
        ra = self.get_reg(a)
        rb = self.get_reg(b)
        opmap = {'+':'ADD','-':'SUB','*':'MUL','/':'DIV'}
        instr = opmap.get(op, 'NOP')
        self.asm.append(f"{instr} {ra}, {rb}")  
        if dest in self.reg_map:
            rd = self.reg_map[dest]
            self.asm.append(f"MOV {rd}, {ra}")
            old = self.reg_map.pop(dest)
            if dest in self.reg_in_use:
                self.reg_in_use.remove(dest)
        old_key = None
        for k,v in list(self.reg_map.items()):
            if v == ra:
                old_key = k
                break
        if old_key and old_key != dest:
            # replace mapping
            self.reg_map.pop(old_key, None)
            if old_key in self.reg_in_use:
                self.reg_in_use.remove(old_key)
        self.reg_map[dest] = ra
        if dest not in self.reg_in_use:
            self.reg_in_use.append(dest)
        return

    def assign(self, dest, src):
        
        rsrc = self.get_reg(src)
       
        self.asm.append(f"STORE {rsrc}, {dest}")
        if dest in self.reg_map:
            self.reg_map.pop(dest)
            if dest in self.reg_in_use:
                self.reg_in_use.remove(dest)

    def iffalse_jump(self, left, op, right, label):
        rl = self.get_reg(left)
        rr = self.get_reg(right)
        self.asm.append(f"CMP {rl}, {rr}")
        jmp = {
            '==':'JNE', '!=':'JE',
            '<':'JGE', '>':'JLE', '<=':'JGT', '>=':'JLT'
        }.get(op, 'JNE')
        self.asm.append(f"{jmp} {label}")

    def ifz_jump(self, operand, label):
        r = self.get_reg(operand)
        self.asm.append(f"CMP {r}, 0")
        self.asm.append(f"JE {label}")

    def emit_label(self, label):
        self.asm.append(f"{label}:")

    def emit_goto(self, label):
        self.asm.append(f"JMP {label}")

    def finalize(self):
        return self.asm[:]
