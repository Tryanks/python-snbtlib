from io import StringIO
from json import dumps as j_dumps, loads as j_loads
from re import compile, sub

annotation = compile(r'^//.*$')
annotation2 = compile(r'^#.*$')


class SnbtReader:
    text = ''
    index = 0

    def __init__(self, t: str):
        # Annotation filter
        t = t.replace('\r', '')
        t = sub(annotation, '', t)
        t = sub(annotation2, '', t)
        self.text = t

    def next(self):
        self.index += 1
        if self.index - 1 >= len(self.text):
            return False
        if self.text[self.index - 1].isspace() and not self.text[self.index - 1] == '\n':
            return self.next()
        return self.text[self.index - 1]

    def snext(self):
        self.index += 1
        if self.index - 1 >= len(self.text):
            return False
        return self.text[self.index - 1]

    def get_point(self):
        return self.text[self.index - 1]

    def last(self):
        self.index -= 1
        return self.text[self.index - 1]


class Token:
    EMPTY = -1
    BEGIN_DICT = 0
    COLON = 2
    END_DICT = 4
    BEGIN_LIST = 5
    END_LIST = 6
    ENTER = 7
    STRING = 8
    STRING_IN_QUOTE = 999
    NUMBER = 9
    BOOL = 10
    INTEGER = 11


class TokenElement:
    type = Token.EMPTY
    value = ''


class TokenIterator:
    TokenList: list = []
    index = 0

    def __init__(self, l):
        self.TokenList = l

    def next(self):
        if self.index >= len(self.TokenList):
            return False
        token = self.TokenList[self.index]
        self.index += 1
        return token


def loads(file, format=False):
    snbt_token = snbt_to_token_list(file)
    snbt_dict = None
    iterator = TokenIterator(snbt_token)
    while i := iterator.next():
        if i.type == Token.BEGIN_DICT:
            snbt_dict = dict_iterator(iterator)
            break
        elif i.type == Token.BEGIN_LIST:
            snbt_dict = list_iterator(iterator)
            break
    if format:
        return j_dumps(snbt_dict, ensure_ascii=False, indent=4)
    return snbt_dict


def dumps(json, indent=0):
    if type(json) == str:
        json = j_loads(json)
    text = ''
    if type(json) == dict:
        if not json:
            text += '{ }\n'
        else:
            text += '{\n'
            indent += 1
            for key, value in json.items():
                text += indent * '\t'
                text += key + ': '
                text += type_return(value, indent)
            text += (indent - 1) * '\t' + '}\n'
    elif type(json) == list:
        if not json:
            text += '[ ]\n'
        elif len(json) == 1 and type(json[0]) not in (dict, list):  # TODO: 解决字典和列表嵌套的缩进问题
            text += f'[{type_return(json[0])[:-1]}]\n'
        else:
            if json[0] == 'I;':
                text += '[I;\n'
                json = json[1:]
            else:
                text += '[\n'
            indent += 1
            for value in json:
                text += indent * '\t' + type_return(value, indent)
            text += (indent - 1) * '\t' + ']\n'

    return text


def type_return(value, indent=0):
    text = ''
    if type(value) in (dict, list):
        text += dumps(value, indent)
    elif type(value) == str:
        if value.startswith('$number$'):
            text += value[8:] + '\n'
        else:
            text += f'"{value}"\n'
    elif type(value) == bool:
        text += 'true' if value else 'false'
        text += '\n'
    return text


def dict_iterator(token):
    tdict = {}
    key = ''
    while i := token.next():
        if i.type == Token.COLON:
            next_i = token.next()
            if next_i.type == Token.BEGIN_DICT:
                tdict[key] = dict_iterator(token)
            elif next_i.type == Token.BEGIN_LIST:
                tdict[key] = list_iterator(token)
            elif next_i.type in (Token.BOOL, Token.STRING, Token.NUMBER, Token.STRING_IN_QUOTE):
                tdict[key] = next_i.value
        elif i.type == Token.END_DICT:
            break
        key = i.value
        if i.type == Token.STRING_IN_QUOTE:
            key = f'"{key}"'
    return tdict


def list_iterator(token):
    tlist = []
    while i := token.next():
        if i.type == Token.BEGIN_DICT:
            tlist.append(dict_iterator(token))
        elif i.type == Token.BEGIN_LIST:
            tlist.append(list_iterator(token))
        elif i.type in (Token.BOOL, Token.STRING, Token.NUMBER, Token.INTEGER, Token.STRING_IN_QUOTE):
            tlist.append(i.value)
        elif i.type == Token.END_LIST:
            break
    return tlist


def snbt_to_token_list(t):
    token_list = []
    reader = SnbtReader(t)
    while i := reader.next():
        token = TokenElement()
        if i == '{':
            token.type = Token.BEGIN_DICT
            token.value = '{'
        elif i == '[':
            token.type = Token.BEGIN_LIST
            token.value = '['
        elif i == ':':
            token.type = Token.COLON
            token.value = ':'
        elif i in '-0123456789':
            token.type = Token.NUMBER
            token.value = NumberBuilder(reader)
        elif i == ']':
            token.type = Token.END_LIST
            token.value = ']'
        elif i == '}':
            token.type = Token.END_DICT
            token.value = '}'
        elif i in ',\n':
            token.type = Token.ENTER
            token.value = '\n'
        else:
            token.value, token.type = StringBuilder(reader)
        token_list.append(token)
    return token_list


def NumberBuilder(r):
    s = StringIO()
    s.write(r.get_point())
    while i := r.next():
        if i in '},\n:' or i.isspace():
            r.last()
            break
        s.write(i)
    return '$number$' + s.getvalue()


def StringBuilder(r):
    s = StringIO()
    type = Token.STRING
    if r.get_point() == '"':
        type = Token.STRING_IN_QUOTE
        while i := r.snext():
            if i == '\\':
                s.write('\\')
                s.write(r.snext())
                continue
            elif i == '"':
                break
            s.write(i)
    else:
        r.last()
        while i := r.next():
            if i in '},\n:[]' or i.isspace():
                r.last()
                break
            s.write(i)
    return s.getvalue(), type
