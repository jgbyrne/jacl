from functools import partial
from enum import Enum

class State:
    def __init__(self):
        self.lno  = 1
        self.col  = 1

    def pos(self, line):
        return (self.lno, self.col, line)


    
class Token:
    def __init__(self, tt, val, pos):
        self.tt = tt
        self.val = val
        self.pos = pos

    def __repr__(self):
        if self.val:
            return "[{}: {}]".format(self.tt.name, self.val)
        else:
            return "[{}]".format(self.tt.name)

class TT(Enum):
    String   = 1
    Integer  = 2
    Float    = 3
    Boolean  = 4

    Equals   = 11
    LBrace   = 12
    RBrace   = 13
    LBrack   = 14
    RBrack   = 15
    LParen   = 16
    RParen   = 17
    Comma    = 18
    Cross    = 19
    Dash     = 20

    Name     = 100

    def tok(self, val, lno, col, line):
        return Token(self, val, (lno, col, line))

symbols = {
    '=': TT.Equals,
    '{': TT.LBrace,
    '}': TT.RBrace,
    '[': TT.LBrack,
    ']': TT.RBrack,
    '(': TT.LParen,
    ')': TT.RParen,
    ',': TT.Comma,
    '+': TT.Cross,
    '-': TT.Dash,
}

def tokenise(p, lno, line):
    toks = []
    ptr = 0
    state = '?'
    tbuf = ""

    for ptr, c in enumerate(line + '\n'):
        if state not in {'s', 'e'} and c == '#':
            break

        # Level 1 States - May fall through to L2 
        if state == 'n':
            if c.isalnum() or c == '_':
                tbuf += c
            else:
                if tbuf.isdigit():
                    if c == '.':
                        tbuf += c
                        state = 'f'
                    else:
                        toks.append(TT.Integer.tok(int(tbuf), lno, ptr, line))
                        tbuf = ""
                        state = '?'
                else:
                    toks.append(TT.Name.tok(tbuf, lno, ptr, line))
                    tbuf = ""
                    state = '?'

        elif state == 'f':
            if c.isdigit():
                tbuf += c
            else:
                toks.append(TT.Float.tok(float(tbuf), lno, ptr, line))
                tbuf = ""
                state = '?'

        # Level 2 States
        if state == '?':
            if tt := symbols.get(c):
                toks.append(tt.tok(None, lno, ptr+1, line))
            
            elif c == '"':
                state = 's'

            elif c.isalnum() or c == '_':
                tbuf += c
                state = 'n'
            
            elif c.isspace():
                continue

            else:
                msg = Message("Unexpected Character",
                              "Could not parse this character",
                              (lno, ptr+1, line))
                p.err(msg)
                return False

        elif state == 's':
            if c == '"':
                toks.append(TT.String.tok(tbuf, lno, ptr+1, line))
                tbuf = ""
                state = '?'
            elif c == '\\':
                state = 'e'
            else:
                tbuf += c

        elif state == 'e':
            tbuf += c
            state = 's'

    return toks
        

def parse(p, state, buf):
    toks = []
    for lno, line in enumerate(buf.split("\n")):
        if (ts := tokenise(p, lno, line)) is not False:
            toks += ts
        else:
            return False


class JaclReader:
    def __init__(self, job, info, warn, err):
        self.job  = job

        self.info = info
        self.warn = warn
        self.err  = err

    def read(self, buf):
        parse(self, None, buf)

# position is a 3-tuple (lno, col, line)
class Message:
    def __init__(self, msg, details, position = None):
        self.msg = msg
        self.details = details
        self.position = position
        if self.position is not None:
            assert len(self.position) == 3
            self.lno = self.position[0]
            self.col = self.position[1]
            self.line = self.position[2]

def main():
    import sys

    def log(lvl, message):
        insight = ""
        if message.position:
            insight = "{:<4}| {}\n".format(message.lno, message.line)
            insight += " " * (5 + message.col) + "^\n"
        print("[{}] {}\n{}{}".format(lvl, message.msg, insight, message.details), file=sys.stderr)

    info = partial(log, "INFO")
    warn = partial(log, "WARN")
    err  = partial(log, "ERROR")

    jr = JaclReader("stdin", info, warn, err)

    jr.read(str(sys.stdin.read()))


if __name__ == "__main__":
    main()
