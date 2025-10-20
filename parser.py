
# Custom parser using tokens from lexer.py and TAC generator.

from tac_generator import TACGenerator
from lexer import Token
import lexer as lexmod


_PRECEDENCE = {
    'uminus': (5, 'right'),
    '*': (4,'left'), '/': (4,'left'),
    '+': (3,'left'), '-': (3,'left'),
    '==': (2,'left'), '!=':(2,'left'), '<':(2,'left'), '>':(2,'left'), '<=':(2,'left'), '>=':(2,'left')
}

class ParserError(Exception):
    pass

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.tac = TACGenerator()
        self.symtab = {}  # name->type

    def cur(self):
        return self.tokens[self.pos]

    def advance(self):
        self.pos += 1
        return self.cur()

    def expect(self, typ=None, val=None):
        t = self.cur()
        if typ and t.type != typ:
            raise ParserError(f"Expected token type {typ} but got {t.type} at line {t.line}")
        if val and t.value != val:
            raise ParserError(f"Expected token value {val} but got {t.value} at line {t.line}")
        self.pos += 1
        return t

    def parse(self):
        while self.cur().type != 'EOF':
            self.parse_statement()
        return self.tac.get_code()

    def parse_statement(self):
        t = self.cur()
        if t.type == 'KEYWORD' and t.value in ('int','float','double','char'):
            self.parse_declaration()
        elif t.type == 'ID':
            self.parse_assignment()
        elif t.type == 'KEYWORD' and t.value == 'print':
            self.parse_print()
        elif t.type == 'KEYWORD' and t.value == 'if':
            self.parse_if()
        elif t.type == 'KEYWORD' and t.value == 'while':
            self.parse_while()
        elif t.type == 'DELIM' and t.value == ';':
            self.advance()
        else:
            raise ParserError(f"Unexpected token {t} at parse_statement")

    def parse_declaration(self):
        typ = self.cur().value
        self.advance()
        
        while True:
            if self.cur().type != 'ID':
                raise ParserError("Expected identifier in declaration")
            name = self.cur().value
            if name in self.symtab:
                raise ParserError(f"Redeclaration of {name}")
            self.symtab[name] = typ
            self.advance()
            if self.cur().type == 'OP' and self.cur().value == '=':
                self.advance()
                val_temp = self.parse_expression_until_delim({',',';'})
                # assign
                self.tac.emit(f"{name} = {val_temp}")
            if self.cur().type == 'DELIM' and self.cur().value == ',':
                self.advance()
                continue
            elif self.cur().type == 'DELIM' and self.cur().value == ';':
                self.advance()
                break
            else:
                raise ParserError("Expected ',' or ';' after declaration")

    def parse_assignment(self):
        name = self.cur().value
        if name not in self.symtab:
            raise ParserError(f"Variable {name} used before declaration")
        self.advance()
        if not (self.cur().type == 'OP' and self.cur().value == '='):
            raise ParserError("Expected '=' in assignment")
        self.advance()
        val_temp = self.parse_expression_until_delim({';'})
        self.tac.emit(f"{name} = {val_temp}")
        # expect ;
        if self.cur().type == 'DELIM' and self.cur().value == ';':
            self.advance()
        else:
            raise ParserError("Missing ';' after assignment")

    def parse_print(self):
        # print ( expr );
        self.advance()  # 'print'
        if not (self.cur().type == 'DELIM' and self.cur().value == '('):
            raise ParserError("Expected '(' after print")
        self.advance()
        val_temp = self.parse_expression_until_delim({')'})
        if not (self.cur().type == 'DELIM' and self.cur().value == ')'):
            raise ParserError("Expected ')' after print expr")
        self.advance()
        if not (self.cur().type == 'DELIM' and self.cur().value == ';'):
            raise ParserError("Expected ';' after print")
        self.advance()
        self.tac.emit(f"PRINT {val_temp}")

    def parse_if(self):
        # if ( cond ) stmt [ else stmt ]
        self.advance()  # 'if'
        if not (self.cur().type == 'DELIM' and self.cur().value == '('):
            raise ParserError("Expected '(' after if")
        self.advance()
        cond = self.parse_condition()
        if not (self.cur().type == 'DELIM' and self.cur().value == ')'):
            raise ParserError("Expected ')' after condition")
        self.advance()
        else_label = self.tac.new_label()
        end_label = self.tac.new_label()
        # emit conditional jump to else_label if cond false
        if isinstance(cond, tuple):
            left_temp, op, right_temp = cond
            self.tac.emit(f"ifFalse {left_temp} {op} {right_temp} goto {else_label}")
        else:
            # cond is single temp -> check if zero
            self.tac.emit(f"ifz {cond} goto {else_label}")
        # then stmt
        self.parse_statement_or_block()
        self.tac.emit(f"goto {end_label}")
        self.tac.emit(f"label {else_label}")
        # else?
        if self.cur().type == 'KEYWORD' and self.cur().value == 'else':
            self.advance()
            self.parse_statement_or_block()
        self.tac.emit(f"label {end_label}")

    def parse_while(self):
        # while ( cond ) stmt
        self.advance()  # while
        if not (self.cur().type == 'DELIM' and self.cur().value == '('):
            raise ParserError("Expected '(' after while")
        self.advance()
        start_label = self.tac.new_label()
        end_label = self.tac.new_label()
        self.tac.emit(f"label {start_label}")
        cond = self.parse_condition()
        if not (self.cur().type == 'DELIM' and self.cur().value == ')'):
            raise ParserError("Expected ')' after condition")
        self.advance()
        if isinstance(cond, tuple):
            left_temp, op, right_temp = cond
            self.tac.emit(f"ifFalse {left_temp} {op} {right_temp} goto {end_label}")
        else:
            self.tac.emit(f"ifz {cond} goto {end_label}")
        self.parse_statement_or_block()
        self.tac.emit(f"goto {start_label}")
        self.tac.emit(f"label {end_label}")

    def parse_statement_or_block(self):
        if self.cur().type == 'DELIM' and self.cur().value == '{':
            self.advance()
            while not (self.cur().type == 'DELIM' and self.cur().value == '}'):
                self.parse_statement()
            self.advance()  # skip '}'
        else:
            self.parse_statement()

    def parse_condition(self):
        
        start = self.pos
        depth = 0
        toks = []
        while True:
            t = self.cur()
            if t.type == 'DELIM' and t.value == '(':
                depth += 1
            if t.type == 'DELIM' and t.value == ')':
                if depth == 0:
                    break
                depth -= 1
            if t.type == 'EOF':
                raise ParserError("Unexpected EOF in condition")
            toks.append(t)
            self.advance()
        
        comp_ops = {'==','!=','<','>','<=','>='}
        comp_index = -1
        comp_val = None
        for idx, tk in enumerate(toks):
            if tk.type == 'OP' and tk.value in comp_ops:
                comp_index = idx
                comp_val = tk.value
                break
        if comp_index == -1:
            postfix = self.shunting_yard(toks)
            temp = self.generate_from_postfix(postfix)
            return temp
        left_toks = toks[:comp_index]
        right_toks = toks[comp_index+1:]
        left_postfix = self.shunting_yard(left_toks)
        right_postfix = self.shunting_yard(right_toks)
        left_temp = self.generate_from_postfix(left_postfix)
        right_temp = self.generate_from_postfix(right_postfix)
        return (left_temp, comp_val, right_temp)

    
    def parse_expression_until_delim(self, delim_set):
        # collect tokens until one of delim_set delimiters (e.g., ';', ',', ')')
        toks = []
        depth = 0
        while True:
            t = self.cur()
            if t.type == 'DELIM' and t.value in delim_set and depth == 0:
                break
            if t.type == 'DELIM' and t.value == '(':
                depth += 1
            if t.type == 'DELIM' and t.value == ')':
                if depth == 0:
                    break
                depth -= 1
            if t.type == 'EOF':
                break
            toks.append(t)
            self.advance()
        postfix = self.shunting_yard(toks)
        temp = self.generate_from_postfix(postfix)
        return temp

    def shunting_yard(self, token_list):
        output = []
        stack = []
        prev_was_op = True
        for tk in token_list:
            if tk.type in ('NUMBER','ID','CHAR'):
                output.append(tk.value if tk.type != 'CHAR' else f"'{tk.value[1:-1]}'")
                prev_was_op = False
            elif tk.type == 'OP':
                op = tk.value
                # detect unary minus
                if op == '-' and prev_was_op:
                    op = 'uminus'
                while stack and stack[-1] != '(':
                    top = stack[-1]
                    
                    p_top = _PRECEDENCE.get(top, (0,))[0]
                    p_op = _PRECEDENCE.get(op, (0,))[0]
                    if ( ( _PRECEDENCE.get(top,(0,))[1] == 'left' and p_top >= p_op ) or
                         ( _PRECEDENCE.get(top,(0))[1] == 'right' and p_top > p_op ) ):
                        output.append(stack.pop())
                    else:
                        break
                stack.append(op)
                prev_was_op = True
            elif tk.type == 'DELIM' and tk.value == '(':
                stack.append('(')
                prev_was_op = True
            elif tk.type == 'DELIM' and tk.value == ')':
                while stack and stack[-1] != '(':
                    output.append(stack.pop())
                if not stack:
                    raise ParserError("Mismatched parentheses")
                stack.pop()
                prev_was_op = False
            else:
                pass
        while stack:
            op = stack.pop()
            if op == '(':
                raise ParserError("Mismatched parentheses")
            output.append(op)
        return output

    def generate_from_postfix(self, postfix):

        stack = []
        for tok in postfix:
            if tok == 'uminus':
                a = stack.pop()
                t = self.tac.new_temp()
                self.tac.emit(f"{t} = uminus {a}")
                stack.append(t)
            elif tok in ('+','-','*','/','==','!=','<','>','<=','>='):
                b = stack.pop()
                a = stack.pop()
                t = self.tac.new_temp()
                self.tac.emit(f"{t} = {a} {tok} {b}")
                stack.append(t)
            else:
                stack.append(str(tok))
        if not stack:
            raise ParserError("Empty expression")
        return stack[-1]
