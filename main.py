# main.py
from lexer import lexer
from parser import Parser, ParserError
from machine_generator import MachineGenerator
import sys
import os

def run_file(filename="sample_code.txt"):
    with open(filename, "r") as f:
        src = f.read()
    print("=== SOURCE CODE ===")
    print(src)
    # Lexical stage
    print("\n=== LEXICAL TOKENS ===")
    toks = lexer(src)
    for t in toks:
        print(t)
    # Parsing/TAC
    print("\n=== PARSING & TAC GENERATION ===")
    p = Parser(toks)
    try:
        p.parse()
    except ParserError as e:
        print("Parser error:", e)
        return
    # Dump symbol table
    print("\n=== SYMBOL TABLE ===")
    for k,v in p.symtab.items():
        print(f"{k} : {v}")
    # Dump TAC
    print("\n=== THREE-ADDRESS CODE (TAC) ===")
    p.tac.dump()
    tac_lines = p.tac.get_code()
    # Machine code generation
    print("\n=== MACHINE CODE (pseudo assembly) ===")
    mg = MachineGenerator(num_registers=4)
    for instr in tac_lines:
        # interpret instr
        parts = instr.split()
        if parts[0] == 'label':
            mg.emit_label(parts[1])
        elif parts[0] == 'goto':
            mg.emit_goto(parts[1])
        elif parts[0] == 'PRINT':
            # operand is parts[1] (maybe temp)
            mg.asm.append(f"PRINT {parts[1]}")
        elif parts[0] == 'ifFalse':
            # ifFalse left op right goto L
            _, left, op, right, _, lbl = parts
            mg.iffalse_jump(left, op, right, lbl)
        elif parts[0] == 'ifz':
            _, operand, _, lbl = parts
            mg.ifz_jump(operand, lbl)
        elif parts[0] == 'label':
            mg.emit_label(parts[1])
        elif parts[0] == 't' or parts[0].startswith('T') or '=' in instr:
            # assignment or temp computation
            if '=' in instr:
                lhs, rhs = instr.split('=',1)
                lhs = lhs.strip(); rhs = rhs.strip()
                if rhs.startswith('uminus '):
                    opnd = rhs.split()[1]
                    r = mg.get_reg(opnd)
                    mg.asm.append(f"NEG {r}")
                    mg.asm.append(f"STORE {r}, {lhs}")
                elif any(op in rhs for op in [' + ',' - ',' * ',' / ','==','!=','<=','>=','<','>']):
                    # binary; parse a op b
                    # split by spaces
                    parts_rhs = rhs.split()
                    a = parts_rhs[0]; oper = parts_rhs[1]; b = parts_rhs[2]
                    mg.binop(lhs, a, oper, b)
                else:
                    # simple assignment
                    mg.assign(lhs, rhs)
        else:
            # fallback: try parse assignment
            if '=' in instr:
                lhs, rhs = instr.split('=',1)
                mg.assign(lhs.strip(), rhs.strip())
    asm = mg.finalize()
    for a in asm:
        print(a)
    # save outputs
    outdir="output"
    os.makedirs(outdir, exist_ok=True)
    with open(outdir+"/tokens.txt","w") as f:
        for t in toks: f.write(repr(t)+"\n")
    with open(outdir+"/tac.txt","w") as f:
        for i,l in enumerate(tac_lines,1): f.write(f"({i}) {l}\n")
    with open(outdir+"/asm.txt","w") as f:
        for a in asm: f.write(a+"\n")

if __name__=="__main__":
    fn = "sample_code.txt"
    if len(sys.argv)>1:
        fn = sys.argv[1]
    run_file(fn)
