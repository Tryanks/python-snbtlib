from io import StringIO
from json import dumps as j_dumps, loads as j_loads


class SnbtReader:
    text = ''
    index = 0

    def __init__(self, t: str):
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


class Token:
    EMPTY = -1
    BEGIN_DICT = 0
    END_DICT = 1
    BEGIN_LIST = 2
    END_LIST = 3
    ENTER = 4
    COLON = 5
    STRING = 6
    NUMBER = 7
    KEY = 8
    BOOL = 9
    INTEGER = 10


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
    while i := token.next():
        if i.type == Token.KEY:
            key = i.value
            next_i = token.next()
            if next_i.type == Token.BEGIN_DICT:
                tdict[key] = dict_iterator(token)
            elif next_i.type == Token.BEGIN_LIST:
                tdict[key] = list_iterator(token)
            elif next_i.type in (Token.BOOL, Token.STRING, Token.NUMBER):
                tdict[key] = next_i.value
        elif i.type == Token.END_DICT:
            break
    return tdict


def list_iterator(token):
    tlist = []
    while i := token.next():
        if i.type == Token.BEGIN_DICT:
            tlist.append(dict_iterator(token))
        elif i.type == Token.BEGIN_LIST:
            tlist.append(list_iterator(token))
        elif i.type in (Token.BOOL, Token.STRING, Token.NUMBER, Token.INTEGER):
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
        elif i in '-0123456789':
            if reader.snext() == ':':
                reader.last()
                token = KeyBuilder(token, reader)
            else:
                reader.last()
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
            token = KeyBuilder(token, reader)
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
    while i := r.snext():
        if i == '\\':
            s.write('\\')
            s.write(r.snext())
            continue
        elif i == '"':
            break
        s.write(i)
    return s.getvalue()


def KeyBuilder(token, r):
    s = ''
    stringStatus = False
    numberStatus = False
    if r.get_point() == '"':
        stringStatus = True
    elif r.get_point() in '0123456789':
        r.last()
        numberStatus = True
    else:
        s += r.get_point()
    token.type = Token.KEY
    while i := r.snext():
        if stringStatus:
            if i == '\\':
                s += '\\'
                s += r.snext()
                continue
            elif i == '"':
                if r.snext() == ':':
                    s = f'"{s}"'
                    break
                else:
                    if not r.get_point().isspace() and not r.get_point() in ',]}':
                        r.last()
                        s += '\\'
                        s += r.get_point()
                        continue
                    else:
                        r.last()
                        token.type = Token.STRING
                        break
        if numberStatus:
            if i in '0123456789':
                s += i
            if r.snext() == ':':
                break
        if i == ':' and not stringStatus:
            break
        s += i
        if s in ('true', 'false'):
            token.type = Token.BOOL
            s = True if s == 'true' else False
            break
        elif s == 'I;':
            token.type = Token.INTEGER
            break
    token.value = s
    return token
