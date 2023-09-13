import argparse
import ast
import collections
import lib2to3
import lib2to3.fixes
import lib2to3.refactor
import math
import sys
import tempfile
from collections.abc import Iterable
from lib2to3 import fixer_base

import napkin.units
import napkin.latency

CONTEXT = {
    # helpful
    'undef': None,

    # math
    'ceil': math.ceil,
    'floor': math.floor,
    'log': math.log,
    'log2': math.log2,
}
CONTEXT.update(napkin.units.CONTEXT)
CONTEXT.update(napkin.latency.CONTEXT)

def is_variable_assignment(node):
    if not isinstance(node, ast.Assign):
        return False
    if node.targets[0].id != node.targets[0].id.upper():
        return False
    assert len(node.targets) == 1
    return True

def assigns_to(node):
    assert is_variable_assignment(node)
    return node.targets[0].id 

def find_outputs(name):
    code = ast.parse(open(name).read())
    outputs = []
    for x in ast.walk(code):
        if not is_variable_assignment(x): continue
        outputs.append(assigns_to(x))
    context = CONTEXT.copy()
    exec(open(name).read(), context)
    return dict([(o, context[o]) for o in outputs])

def find_deps(name):
    code = ast.parse(open(name).read())
    deps = {}
    for x in ast.walk(code):
        if not is_variable_assignment(x): continue
        name = assigns_to(x)
        deps[name] = []
        for y in ast.walk(x):
            if isinstance(y, ast.Name) and y.id not in CONTEXT and y.id != name:
                deps[name].append(y.id)
    return deps

def transitive_closure(deps, name):
    out = [name]
    for n in deps.get(name, []):
        out += transitive_closure(deps, n)
    return out

VALID_UNITS = [
    'bytes',
    'bytes/sec',
    'seconds',
    'sigfig',
    'percent',
    'raw',
    'hide',
    'percentiles',
]

for _x in tuple(VALID_UNITS):
    VALID_UNITS.append('percentiles:' + _x)

def humanize_bytes(x):
    return napkin.units.humanize_metric(x, base=1024) + 'iB'

def humanize_bytes_sec(x):
    return humanize_bytes(x) + '/s'

def humanize_seconds(x, recurse=False):
    '''Turn a number into a string of the time

    >>> humanize_seconds(0)
    '0s'
    >>> humanize_seconds(60)
    '1m'
    >>> humanize_seconds(120)
    '2m'
    >>> humanize_seconds(128)
    '2m8s'
    >>> humanize_seconds(86400)
    '1d'
    >>> humanize_seconds(86401)
    '1d1s'

    >>> humanize_seconds(1.01)
    '1s10ms'
    >>> humanize_seconds(3.14159)
    '3s141ms589µs999ns'
    >>> humanize_seconds(51e-9)
    '51ns'
    '''
    for interval, unit in [(86400, 'd'), (3600, 'h'), (60, 'm'), (1, 's'),
            (1e-3, 'ms'), (1e-6, 'µs'), (1e-9, 'ns')]:
        if x >= interval:
            return '%d%s%s' % (x / interval, unit, humanize_seconds(x % interval, True))
    if recurse:
        return ''
    return '0s'

def humanize_sigfig(x):
    return '%1.2g' % x

def humanize_percent(x):
    return '%.1f%%' % (100 * x)

def humanize_raw(x):
    return str(x)

class Tool:

    def __init__(self, outputs):
        self.outputs = outputs

    def substitute(self, output, units=None):
        output = self.outputs[output]
        return self._substitute(output, units)

    def _substitute(self, output, units):
        if units == 'hide':
            return '...'
        if isinstance(output, napkin.latency.SLA):
            PERCENTILES_PREFIX = 'percentiles:'
            if units and units.startswith(PERCENTILES_PREFIX):
                units = units[len(PERCENTILES_PREFIX):]
            if units == 'percentiles':
                units = 'raw'
            return 'SLA(' + ', '.join(('({}, {})'.format(x, self._substitute(round(fx, 3), units)) for (x, fx) in output.percentiles[1:])) + ')'
        if isinstance(output, napkin.latency.PMF):
            return 'PMF(...)'
        if isinstance(output, napkin.latency.CDF):
            return 'CDF(...)'
        if isinstance(output, Iterable):
            return '[' + ', '.join((self._substitute(x, units) for x in output)) + ']'
        if units is not None:
            units = {
                'bytes/sec': 'bytes_sec'
            }.get(units, units)
            f = globals().get('humanize_' + units, None)
            assert f is not None, 'cannot find humanize_{}'.format(units)
            return f(output)
        if isinstance(output, bool):
            return 'True' if output else 'False'
        if isinstance(output, (float, int)):
            return napkin.units.humanize_metric(output)
        if output is None:
            return 'undefined'
        assert False

    def interpret_comment(self, text):
        text = text.strip(' #')
        if text == '': return None, ''
        if text in VALID_UNITS:
            return text, ''
        return None, ' # ' + text

def changes(filename, name):
    deps = find_deps(filename)
    return sorted(set(transitive_closure(deps, name)))

def is_changed_by(filename, name):
    outs = []
    deps = find_deps(filename)
    for output in deps.keys():
        if name == output:
            continue
        if name in transitive_closure(deps, output):
            outs.append(output)
    return sorted(set(outs))

def constants(filename):
    outputs = find_outputs(filename)
    deps = find_deps(filename)
    for o in outputs:
        if not deps[o]:
            yield o

def translate(filename):
    outputs = find_outputs(filename)
    rt = lib2to3.refactor.RefactoringTool(('napkin.substitute',), {'NAPKIN': Tool(outputs)})
    contents = open(filename).read()
    translated = (rt.refactor_string(contents, filename))
    return str(translated).rstrip()

def main():
    parser = argparse.ArgumentParser(prog='napkin')
    # TODO(rescrv):
    # - allow sweeping a parameter
    parser.add_argument('--changes', metavar='V', type=str,
            help='what variables change the provided argument')
    parser.add_argument('--is-changed-by', metavar='V', type=str,
            help='what variables are changed by the provided argument')
    parser.add_argument('--constants', '-c', action='store_true',
            dest='constants', default=None,
            help='print all contants')
    parser.add_argument('input', nargs='*', help='input napkin filename')

    args = parser.parse_args()

    actions = [v for v in [
        args.changes,
        args.is_changed_by,
        args.constants,
    ] if v is not None]
    if len(actions) > 1:
        print('provided too many different actions', file=sys.stderr)
        sys.exit(1)

    if args.changes:
        for x in changes(args.input, args.changes):
            print(x)
    if args.is_changed_by:
        c = constants(args.input)
        for x in is_changed_by(args.input, args.is_changed_by):
            print(x)
    if args.constants:
        for c in sorted(constants(args.input)):
            print(c)
    if len(actions) == 0:
        content = ''
        for x in args.input:
            content += open(x).read() + '\n'
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(content.encode('utf8'))
            tmp.flush()
            print(translate(tmp.name).rstrip())

if __name__ == '__main__':
    main()
