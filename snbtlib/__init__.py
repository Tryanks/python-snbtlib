from snbtlib.formatter import dumps as d, loads as l


def dump(obj, fp, **kwargs):
    fp.write(d(obj, **kwargs))


def dumps(obj, **kwargs):
    return d(obj, **kwargs)


def load(fp, **kwargs):
    return l(fp.read(), **kwargs)


def loads(s, **kwargs):
    return l(s, **kwargs)

