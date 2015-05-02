#!/usr/bin/env python

"""
Given a string, expand that string using POSIX [parameter expansion][1].

## Limitations

(Pull requests to remove limitations are welcome.)

- Nested expansions `${foo:-$bar}` are not supported.
- Only ASCII alphanumeric characters and underscores are supported in parameter
names. (Per POSIX, parameter names may not begin with a numeral.)
- Assignment expansions do not mutate the real environment.

[1]: http://pubs.opengroup.org/onlinepubs/009695399/utilities/xcu_chap02.html#tag_02_06_02
"""

from itertools import takewhile
from os import getenv
from shlex import shlex

def expand(s, env=None):
    """Expand the string using POSIX parameter expansion rules.
    Uses the provided environment dict or the actual environment."""
    if env is None:
        env = dict(os.environ)
    return ''.join(expand_tokens(s, env))

def expand_tokens(s, env):
    shl = shlex(s, posix=True)
    while True:
        # This apparently infinite loop should eventually
        # raise StopIteration and thus exit.
        yield ''.join(takewhile(lambda t: t != "$", shl))
        yield follow_sigil(shl, env)

def follow_sigil(shl, env):
    param = next(shl)
    if param == "{":
        return follow_brace(takewhile(lambda t: t != "}", shl), env)
    return env.get(param, "")

def follow_brace(shl, env):
    param = next(shl)
    if param == "#":
        word = next(shl)
        subst = env.get(word, "")
        return len(subst)
    subst = env.get(param, "")
    param_set_and_not_null = bool(subst and (param in env))
    param_set_but_null = bool((param in env) and not subst)
    param_unset = param not in env
    try:
        modifier = next(shl)
        if modifier == ":":
            modifier = next(shl)
            if modifier == "-":
                word = next(shl)
                if param_set_and_not_null:
                    return subst
                return word
            elif modifier == "=":
                word = next(shl)
                if param_set_and_not_null:
                    return subst
                env[param] = word
                return env[param]
            elif modifier == "?":
                if param_set_and_not_null:
                    return subst
                raise ParameterExpansionNullError(shl)
            elif modifier == "+":
                if param_set_and_not_null:
                    return next(shl)
                return subst # ""
            else:
                raise ParameterExpansionParseError()
        else:
            if modifier == "-":
                word = next(shl)
                if param_unset:
                    return word
                return subst # may be ""
            elif modifier == "=":
                word = next(shl)
                if param_unset:
                    env[param] = word
                    return env[param]
                return subst # may be ""
            elif modifier == "?":
                if param_unset:
                    raise ParameterExpansionNullError(shl)
                return subst # may be ""
            elif modifier == "+":
                word = next(shl)
                if param_unset:
                    return subst # ""
                return word
            raise ParameterExpansionParseError()
    except StopIteration:
        return subst
