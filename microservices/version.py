MAJOR = 0
MINOR = 21
PATCH = 4


def get_version(suffix=''):
    return '.'.join([str(v) for v in (MAJOR, MINOR, PATCH)]) + suffix


if __name__ == '__main__':
    print(get_version())
