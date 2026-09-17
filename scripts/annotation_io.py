"""Read retained annotation formats without altering the stored JSON."""


def entries(value):
    if isinstance(value, dict) and 'value' in value and 'evidence' in value:
        return [value]
    if isinstance(value, list) and value and all(isinstance(e, dict) for e in value):
        return value
    if isinstance(value, list) and len(value) == 2 and all(isinstance(e, str) for e in value):
        return [{'value': value[0], 'evidence': value[1]}]
    raise ValueError(f'Unrecognized annotation representation: {value!r}')


def is_legacy_pair(value):
    return isinstance(value, list) and len(value) == 2 and all(isinstance(e, str) for e in value)


def representation(value):
    if isinstance(value, dict):
        return 'single_object'
    return 'legacy_pair' if is_legacy_pair(value) else 'object_list'
