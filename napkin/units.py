import math

METRIC_PREFIXES_POSITIVE = ['', 'k', 'M', 'G', 'T', 'P', 'E']
METRIC_PREFIXES_NEGATIVE = ['', 'm', 'µ', 'n', 'p']

def _si_frexp(x, base=1000):
    '''Convert number to normalized fraction and exponent components.

    Here's what it looks like with base 1000:
    >>> _si_frexp(1)
    (1.0, 0)
    >>> _si_frexp(10)
    (10.0, 0)
    >>> _si_frexp(100)
    (100.0, 0)
    >>> _si_frexp(1000)
    (1.0, 1)
    >>> _si_frexp(10000)
    (10.0, 1)
    >>> _si_frexp(100000)
    (100.0, 1)
    >>> _si_frexp(1000000)
    (1.0, 2)
    >>> _si_frexp(1000000000)
    (1.0, 3)

    And here's base 1024 (e.g., for 1MiB):
    >>> _si_frexp(1, base=1024)
    (1.0, 0)
    >>> _si_frexp(16, base=1024)
    (16.0, 0)
    >>> _si_frexp(128, base=1024)
    (128.0, 0)
    >>> _si_frexp(1024, base=1024)
    (1.0, 1)
    >>> _si_frexp(16384, base=1024)
    (16.0, 1)
    >>> _si_frexp(131072, base=1024)
    (128.0, 1)
    >>> _si_frexp(1047552, base=1024)
    (1023.0, 1)
    >>> _si_frexp(1048576, base=1024)
    (1.0, 2)

    Small values work too!  Yay for logarithms:
    >>> _si_frexp(.1)
    (100.0, -1)
    >>> _si_frexp(.01)
    (10.0, -1)
    >>> _si_frexp(.001)
    (1.0, -1)

    Further testing of small values omitted because floating point gets wonky
    and hard to present down there.
    '''
    if x == 0: return (0, 0)
    exponent = math.floor(math.log(x, base))
    return x / base**exponent, exponent

def humanize_metric(x, base=1000):
    '''Translate a string into a number with metric suffix.

    It looks something like this:
    >>> humanize_metric(0)
    '0'
    >>> humanize_metric(1)
    '1'
    >>> humanize_metric(1_000)
    '1k'
    >>> humanize_metric(10_000)
    '10k'
    >>> humanize_metric(100_000)
    '100k'
    >>> humanize_metric(1_000_000)
    '1M'
    >>> humanize_metric(1_000_000_000)
    '1G'
    >>> humanize_metric(1_000_000_000_000)
    '1T'
    >>> humanize_metric(1_000_000_000_000_000)
    '1P'
    >>> humanize_metric(1_000_000_000_000_000_000)
    '1E'

    Or like this in base 1024:
    >>> humanize_metric(1, base=1024)
    '1'
    >>> humanize_metric(1_024, base=1024)
    '1k'
    >>> humanize_metric(16_384, base=1024)
    '16k'
    >>> humanize_metric(131_072, base=1024)
    '128k'
    >>> humanize_metric(1_047_552, base=1024)
    '1023k'
    >>> humanize_metric(1_048_576, base=1024)
    '1M'

    And something like this for the small values:
    >>> humanize_metric(.1)
    '100m'
    >>> humanize_metric(.01)
    '10m'
    >>> humanize_metric(.001)
    '1m'
    >>> humanize_metric(.0001)
    '100µ'
    >>> humanize_metric(.00001)
    '10µ'
    >>> humanize_metric(.000001)
    '1µ'
    >>> humanize_metric(.000000001)
    '1n'
    >>> humanize_metric(.000000000001)
    '1p'

    Let's test the limits and how things get clipped when large:
    >>> humanize_metric(602214857740000000000000)
    '602214E'
    >>> humanize_metric(.000000000000314)
    '0.31p'
    '''
    frac, exp = _si_frexp(x, base)
    while exp < 0 and 0-exp >= len(METRIC_PREFIXES_NEGATIVE):
        frac /= base
        exp += 1
    while exp > 0 and exp >= len(METRIC_PREFIXES_POSITIVE):
        frac *= base
        exp -= 1
    #while exp < 0 and 0-exp <= len(
    #    frac /= base
    #    exp += 1
    if frac >= 100:
        xs = '%d' % frac
    elif x >= 10:
        xs = '%2.1f' % frac
    else:
        xs = '%1.2f' % frac
    if '.' in xs:
        xs = xs.rstrip('0')
        xs = xs.rstrip('.')
    if exp >= 0:
        return xs + METRIC_PREFIXES_POSITIVE[exp]
    else:
        return xs + METRIC_PREFIXES_NEGATIVE[0-exp]

CONTEXT = {
    'nanos': 1e-9,
    'micros': 1e-6,
    'millis': 1e-3,
}

for idx, suffix in enumerate(METRIC_PREFIXES_POSITIVE):
    if not suffix: continue
    CONTEXT[suffix] = 1000**(idx)
    CONTEXT[suffix + 'i'] = 1024**(idx)
for idx, suffix in enumerate(METRIC_PREFIXES_NEGATIVE):
    if not suffix: continue
    CONTEXT[suffix] = 1000**(0-idx)
