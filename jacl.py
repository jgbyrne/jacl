from functools import partial
from enum import Enum

class JaclError(Exception):
    def __init__(self, message):
        self.message = message
    
    def __str__(self):
        return self.message

class Jacl:
    @classmethod
    def from_file(cls, path):
        with open(path) as inf:
            return cls.from_string(inf.read(), job_name=path)

    @classmethod
    def from_string(cls, string, job_name=None):
        import sys

        def log(lvl, message):
            insight = ""
            if message.position:
                insight = "{:<4}| {}\n".format(message.lno, message.line)
                insight += " " * (5 + message.col) + "^\n"
            raise JaclError("[{}] {}\n{}{}".format(lvl, message.msg, insight, message.details))

        info = partial(log, "INFO")
        warn = partial(log, "WARN")
        err  = partial(log, "ERROR")

        jr = JaclReader(job_name if job_name else "string", info, warn, err)
        return jr.read(string)

    def __init__(self, obj):
        assert isinstance(obj, JaclTable)
        self._obj = obj

    def __getattr__(self, name):
        if name == "key":
            return self._obj.key

        if isinstance(self._obj, JaclObject):
            val = self._obj.bindings.get(name)
            if isinstance(val, JaclTable):
                return Jacl(val)
            elif isinstance(val, Name):
                return self[val.val]
            else:
                return val
        else:
            raise AttributeError

    def __getitem__(self, key):
        if isinstance(key, Name):
            key = key.val
        if (entry := self._obj.entries.get(key)) is not None:
            return Jacl(entry)
        return None

    def __iter__(self):
        for entry in self._obj.entries.values():
            yield Jacl(entry)

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

class JaclReader:
    def __init__(self, job, info, warn, err):
        self.job  = job

        self.info = info
        self.warn = warn
        self.err  = err

        self.toks = None
        self.doc  = None

    def tok_peek(self):
        if not self.toks:
            return None
        return self.toks[0]

    def tok_pop(self):
        if not self.toks:
            return None
        return self.toks.pop(0)

    def tok_expect(self, tt, err_msg, err_details):
        if tok := self.tok_pop(): 
            if tok.tt != tt:
                msg = Message(err_msg, err_details, tok.pos)
                self.err(msg)
        else:
            msg = Message(err_msg, err_details)
            self.err(msg)

        return True

    def permit_break(self):
        while (tok := self.tok_peek()) is not None and tok.tt == TT.Break:
            self.tok_pop()

    def read(self, buf):
        parse(self, None, buf)
        return Jacl(self.doc)

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
    Break    = 1000

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
    ';': TT.Break,
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
                        toks.append(TT.Integer.tok(int(tbuf), lno, ptr+1, line))
                        tbuf = ""
                        state = '?'
                else:
                    if tbuf == "true":
                        toks.append(TT.Boolean.tok(True, lno, ptr+1, line))
                    elif tbuf == "false":
                        toks.append(TT.Boolean.tok(False, lno, ptr+1, line))
                    else:
                        toks.append(TT.Name.tok(tbuf, lno, ptr+1, line))
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

    toks.append(TT.Break.tok(None, lno, ptr, line))
    return toks

class JaclTable:
    def __init__(self):
        self.entries = {}

    def recursive_repr(self, indent=0):
        s = "    " * indent + "[" + "\n"
        for key, entry in self.entries.items():
            s += "    " * indent + "  [{}]".format(key) + "\n"
            s += entry.recursive_repr(indent + 1)
        s += "    " * indent + "]" + "\n\n"
        return s

    def __repr__(self):
        return self.recursive_repr(0)


class JaclObject(JaclTable):
    def __init__(self, key):
        super().__init__()
        self.key = key
        self.bindings = {}

    def recursive_repr(self, indent=0):
        s = "    " * indent + "{" + "\n"


        for key, entry in self.entries.items():
            s += "    " * indent + "  [{}]".format(key) + "\n"
            s += entry.recursive_repr(indent + 1)

        if self.entries and self.bindings:
            s += "\n" + "    " * indent + "  ----" + "\n\n"

        for name, value in self.bindings.items():
            s += "    " * indent + "  {}:".format(name) + "\n"
            if isinstance(value, JaclTable):
                s += value.recursive_repr(indent + 1)
            else:
                s += "    " * (indent + 1) + repr(value) + "\n"
        s += "    " * indent + "}" + "\n\n"
        return s

    def __repr__(self):
        return self.recursive_repr(0)

class Name:
    def __init__(self, val):
        self.val = val

    def __repr__(self):
         return "{}".format(self.val)

def literal(p):
    if tok := p.tok_pop():
        if tok.tt in {TT.String, TT.Integer, TT.Float, TT.Boolean}:
            return tok.val
        else:
            p.err(Message("Unexpected Value",
                          "This value cannot go here", tok.pos))
    else:
        p.err(Message("Unexpected End-of-File",
                      "Expected value but document ended abruptly"))

def val_or_key(p):
    if tok := p.tok_pop():
        if tok.tt == TT.LParen:
            p.permit_break()
            items = []
            while True:
                if nxt := p.tok_peek():
                    if nxt.tt == TT.RParen:
                        p.tok_pop()
                        break

                    if nxt.tt in {TT.Name, TT.LParen}:
                        items.append(val_or_key(p))
                    else:
                        items.append(literal(p))

                if post := p.tok_peek():
                    if post.tt == TT.RParen:
                        p.tok_pop()
                        break
                    else:
                        p.tok_expect(TT.Comma, "Could not parse tuple",
                                               "Expected ','")
                        p.permit_break()
                else:
                    p.err(Message("Unclosed Tuple",
                                  "Expected ')' here",
                                  tok.pos))
            return tuple(items)
        elif tok.tt == TT.Name:
            return Name(tok.val)
        else:
            p.err(Message("Expected Name or Tuple", "Found {}".format(tok.tt.name), tok.pos))
    else:
        p.err(Message("Unexpected End-of-File",
                      "Expected value or key"))

def rval(p, scopes):
    if tok := p.tok_peek():
        if tok.tt == TT.LBrace:
            children = []
            child_keys = []
            for scope in scopes:
                child_key = "#anon" + str(len(scope.entries) + 1)
                child = JaclObject(child_key)
                scope.entries[child_key] = child
                children.append(child)
                child_keys.append(Name(child_key))
            object_struct(p, children)
            return child_keys 

        if tok.tt == TT.LBrack:
            return [table(p)] * len(scopes)

        if tok.tt in {TT.Name, TT.LParen}:
            vk = val_or_key(p)
            if (nxt := p.tok_peek()) is not None:
                if nxt.tt == TT.LBrace:
                    if type(vk) is Name:
                        keys = (vk.val,)
                    else:
                        if not all(type(k) is Name for k in vk):
                            p.err(Message("Invalid type for key",
                                          "Keys must be plain names",
                                          tok.pos))
                        keys = [k.val for k in vk]

                        objs = []
                        for scope in scopes:
                            for key in keys:
                                obj = scope.entries.get(key)
                                if obj is None:
                                    obj = JaclObject(key)
                                    scope.entries[key] = obj
                                objs.append(obj)
                        object_struct(p, objs)
            return [vk] * len(scopes)

        return [literal(p)] * len(scopes)
    else:
       p.err(Message("Unexpected End-of-File", "Expected Value")) 


def stmt(p, scopes):
    if tok := p.tok_peek():
        if tok.tt == TT.LBrace:
            children = []
            for scope in scopes:
                child_key = "#anon" + str(len(scope.entries) + 1)
                child = JaclObject(child_key)
                scope.entries[child_key] = child
                children.append(child)
            object_struct(p, children)
            return
        else:
            key = val_or_key(p)

            if type(key) is Name:
                keys = (key.val,)
            else:
                if not all(type(k) is Name for k in key):
                    p.err(Message("Invalid type for key",
                                  "Keys must be plain names",
                                  tok.pos))
                keys = [k.val for k in key]

            if (nxt := p.tok_peek()) is not None:
                if nxt.tt == TT.Equals:
                    if not all(type(scope) is JaclObject for scope in scopes):
                        p.err(Message("Binding in Table",
                                      "Only Objects may contain bindings",
                                      tok.pos))
                    props = keys
                    p.tok_pop()
                    vals = rval(p, scopes)

                    for val, scope in zip(vals, scopes):
                        for prop in props:
                            if prop == "key":
                                p.err(Message("Invalid Property Name",
                                              "'key' is a reserved name",
                                              tok.pos))
                            scope.bindings[prop] = val

                    return

                elif nxt.tt == TT.LBrace:
                    objs = []
                    for scope in scopes:
                        for key in keys:
                            obj = scope.entries.get(key)
                            if obj is None:
                                obj = JaclObject(key)
                                scope.entries[key] = obj
                            objs.append(obj)
                    object_struct(p, objs)
                    return

            for scope in scopes:
                for key in keys:
                    if key in scope.entries:
                        p.warn(Message("Meaningless Object Redefinition",
                                       "Redefining '{}' with no data achieves nothing".format(key),
                                       tok.pos))
                    else:
                        obj = JaclObject(key)
                        scope.entries[key] = obj
    else:
       p.err(Message("Unexpected End-of-File", "Expected Statement")) 

def table(p):
    p.tok_expect(TT.LBrack, "Could not parse Table",
                            "Expected '['")

    table = JaclTable()
    
    p.permit_break()
    while (tok := p.tok_peek()) is not None:
        if tok.tt == TT.RBrack:
            break
        
        stmt(p, (table,))
        p.permit_break()

    p.tok_expect(TT.RBrack, "Could not parse Table",
                            "Expected ']'")
    return table


def object_inner(p, objs):
    while True:
        p.permit_break()

        # End conditions for inner are EOF or '}'
        # It is the parent's responsibility to check its condition
        if p.tok_peek() is None:
            return

        if p.tok_peek().tt == TT.RBrace:
            return
        
        stmt(p, objs)
        p.permit_break()

def object_struct(p, objs):
    p.tok_expect(TT.LBrace, "Could not parse Object",
                            "Expected '{'")

    object_inner(p, objs)

    p.tok_expect(TT.RBrace, "Could not parse Object",
                            "Expected '}'")

def document(p):
    root = JaclObject("#root")
    p.doc = root
    object_inner(p, (root,))

def parse(p, state, buf):
    toks = []
    for i, line in enumerate(buf.split("\n")):
        if (ts := tokenise(p, i+1, line)) is not False:
            toks += ts
        else:
            return False
    
    p.toks = toks
    document(p)

    if p.tok_peek() is not None:
        p.err(Message("Dangling Tokens", 
                      "Parsing concluded but tokens remained"))
