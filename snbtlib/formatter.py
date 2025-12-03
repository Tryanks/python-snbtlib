from __future__ import annotations

from io import StringIO
from json import dumps as j_dumps, loads as j_loads
from re import compile, sub
from typing import Any, Dict, List, Tuple, Union

annotation = compile(r'^\s+?//.*$')
annotation2 = compile(r'^\s+?#.*$')


class SnbtReader:
    text: str = ''
    index: int = 0

    def __init__(self, t: str) -> None:
        # Annotation filter
        t = t.replace('\r', '')
        t = sub(annotation, '', t)
        t = sub(annotation2, '', t)
        self.text = t

    def next(self) -> Union[str, bool]:
        self.index += 1
        if self.index - 1 >= len(self.text):
            return False
        if self.text[self.index - 1].isspace() and not self.text[self.index - 1] == '\n':
            return self.next()
        return self.text[self.index - 1]

    def snext(self) -> Union[str, bool]:
        self.index += 1
        if self.index - 1 >= len(self.text):
            return False
        return self.text[self.index - 1]

    def get_point(self) -> str:
        return self.text[self.index - 1]

    def last(self) -> str:
        self.index -= 1
        return self.text[self.index - 1]


class Token:
    EMPTY: int = -1
    BEGIN_DICT: int = 0
    COLON: int = 2
    END_DICT: int = 4
    BEGIN_LIST: int = 5
    END_LIST: int = 6
    ENTER: int = 7
    STRING: int = 8
    STRING_IN_QUOTE: int = 999
    NUMBER: int = 9
    BOOL: int = 10
    INTEGER: int = 11


class TokenElement:
    type: int = Token.EMPTY
    value: Union[str, bool] = ''


class TokenIterator:
    TokenList: List[TokenElement] = []
    index: int = 0

    def __init__(self, l: List[TokenElement]) -> None:
        self.TokenList = l

    def next(self) -> Union[TokenElement, bool]:
        if self.index >= len(self.TokenList):
            return False
        token = self.TokenList[self.index]
        self.index += 1
        return token

    def last(self) -> TokenElement:
        self.index -= 1
        return self.TokenList[self.index - 1]


def loads(file: str, format: bool = False) -> Union[Dict[str, Any], List[Any], str, None]:
    snbt_token = snbt_to_token_list(file)
    snbt_dict: Union[Dict[str, Any], List[Any], None] = None
    iterator = TokenIterator(snbt_token)
    while i := iterator.next():
        if i.type == Token.BEGIN_DICT:
            snbt_dict = dict_iterator(iterator)
            break
        elif i.type == Token.BEGIN_LIST:
            snbt_dict = list_iterator(iterator)  # type: ignore[assignment]
            break
    if format:
        return j_dumps(snbt_dict, ensure_ascii=False, indent=4)
    return snbt_dict


def dumps(json: Union[str, Dict[str, Any], List[Any]], indent: int = 0, compact: bool = False) -> str:
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

    return text if not compact else Compatible(text)


def type_return(value: Any, indent: int = 0) -> str:
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
    elif type(value) == bytes:
        text += "[B;\n"
        for i in value:
            text += '\t' * (indent + 1) + str(int.from_bytes(i, 'big')) + 'b\n'
        text += '\t' * indent + ']\n'
    return text


def dict_iterator(token: TokenIterator) -> Dict[str, Any]:
    tdict: Dict[str, Any] = {}
    key: str = ''
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
        key = i.value  # type: ignore[assignment]
        if isinstance(key, str) and key.startswith('$number$'):
            key = key[8:]
        if i.type == Token.STRING_IN_QUOTE and isinstance(key, str):
            key = f'"{key}"'
    return tdict


def list_iterator(token: TokenIterator) -> Union[List[Any], bytes]:
    tlist: List[Any] = []
    if token.next() == "B;":
        tlist_bytes: bytes = b''
        while i := token.next():
            if i.type == Token.END_LIST:
                break
            value = i.value[:-1]  # type: ignore[index]
            tlist_bytes += int(value).to_bytes(1, 'big')
        return tlist_bytes
    else:
        token.last()
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


def snbt_to_token_list(t: str) -> List[TokenElement]:
    token_list: List[TokenElement] = []
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


def NumberBuilder(r: SnbtReader) -> str:
    s = StringIO()
    s.write(r.get_point())
    while i := r.next():
        if i in '}],\n:' or i.isspace():
            r.last()
            break
        s.write(i)  # type: ignore[arg-type]
    return '$number$' + s.getvalue()


def StringBuilder(r: SnbtReader) -> Tuple[Union[str, bool], int]:
    s = StringIO()
    type_val = Token.STRING
    if r.get_point() == '"':
        type_val = Token.STRING_IN_QUOTE
        while i := r.snext():
            if i == '\\':
                s.write('\\')
                s.write(r.snext())
                continue
            elif i == '"':
                break
            s.write(i)  # type: ignore[arg-type]
    else:
        r.last()
        while i := r.next():
            if i in '},\n:[]' or i.isspace():
                r.last()
                break
            s.write(i)  # type: ignore[arg-type]
    if type_val == Token.STRING and s.getvalue() in ('true', 'false'):
        return s.getvalue() == 'true', Token.BOOL
    return s.getvalue(), type_val


def Compatible(text: str) -> str:  # Thanks for XDawned
    if not text:
        return ''
    else:
        lines = text.splitlines()
        for i in range(len(lines)-1):
            if lines[i][-1] not in '[{' and lines[i+1].strip()[0] not in ']}':
                lines[i] += ','
        return '\n'.join(lines)
