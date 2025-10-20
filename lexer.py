
# Custom lexer. Returns list of tokens (type, value, line, col)...

import re

KEYWORDS = {'int','float','double','char','if','else','while','print','return'}
OPS = {'+', '-', '*', '/', '=', '==','!=','<','>','<=','>='}
DELIMS = {';', ',', '(', ')', '{', '}'}

token_specification = [
    ('NUMBER',   r'\d+(\.\d+)?'),        
    ('CHAR',     r'\'(.)\''),             
    ('ID',       r'[A-Za-z_][A-Za-z0-9_]*'),
    ('OP2',      r'==|!=|<=|>='),
    ('OP1',      r'[+\-*/=<>]'),
    ('DELIM',    r'[;,(){}]'),
    ('SKIP',     r'[ \t]+'),
    ('NEWLINE',  r'\n'),
    ('MISMATCH', r'.'),
]

_tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
_get_token = re.compile(_tok_regex).match

class Token:
    def __init__(self, typ, val, line, col):
        self.type = typ
        self.value = val
        self.line = line
        self.col = col
    def __repr__(self):
        return f"Token({self.type!r}, {self.value!r}, line={self.line},col={self.col})"

def lexer(code):
    """Return list of Token objects from source code string."""
    pos = 0
    line = 1
    col = 1
    tokens = []
    mo = _get_token(code, pos)
    while mo:
        typ = mo.lastgroup
        val = mo.group(typ)
        if typ == 'NEWLINE':
            line += 1
            col = 1
        elif typ == 'SKIP':
            col += len(val)
        elif typ == 'MISMATCH':
            raise RuntimeError(f'Unexpected character {val!r} on line {line} col {col}')
        else:
            if typ == 'ID':
                if val in KEYWORDS:
                    tok_type = 'KEYWORD'
                else:
                    tok_type = 'ID'
            elif typ == 'OP2':
                tok_type = 'OP'
            elif typ == 'OP1':
                tok_type = 'OP'
            elif typ == 'DELIM':
                tok_type = 'DELIM'
            elif typ == 'NUMBER':
                tok_type = 'NUMBER'
            elif typ == 'CHAR':
                tok_type = 'CHAR'
            else:
                tok_type = typ
            tokens.append(Token(tok_type, val, line, col))
            col += len(val)
        pos = mo.end()
        mo = _get_token(code, pos)
    tokens.append(Token('EOF','',line,col))
    return tokens
