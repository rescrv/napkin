import math

import numpy
import scipy.signal
import scipy.stats

class InvalidPercentile(Exception): pass
class InvalidScale(Exception): pass

class SLA:
    @classmethod
    def from_pmf(cls, pmf, *percentiles):
        return SLA.from_cdf(pmf.to_cdf(), *percentiles)

    @classmethod
    def from_cdf(cls, cdf, *percentiles):
        ret = []
        for p in percentiles:
            ret.append((p, cdf.percentile(p)))
        return SLA(*ret)

    def __init__(self, *percentiles):
        percentiles = ((0, 0),) + percentiles
        # There must be percentiles
        assert percentiles
        # There's no points outside [0.0, 1.0]
        assert all(0 <= x <= 1 for x, _ in percentiles)
        # There's no duplicate x coordinates
        assert len(percentiles) == len(set(x for x, _ in percentiles))
        # Make sure that percentiles is monotonic.
        percentiles = sorted(percentiles)
        for idx in range(1, len(percentiles)):
            if percentiles[idx - 1][0] >= percentiles[idx][0] or percentiles[idx - 1][1] > percentiles[idx][1]:
                raise InvalidPercentile("percentiles[{}] > percentiles[{}]", idx - 1, idx)
        # Start with (0, 0) and end with (1.0, Y).
        if not percentiles or percentiles[0][0] != 0 or percentiles[0][1] != 0:
            raise InvalidPercentile("percentiles[0] must be (0, 0)")
        if not percentiles or percentiles[-1][0] != 1.0:
            raise InvalidPercentile("percentiles[-1] must be (1.0, fx)")
        self.percentiles = percentiles
        self.min_scale = 10 * math.ceil(1 / min((fx for x, fx in self.percentiles if x > 0)))

    def pmf(self, scale=1000):
        if scale < self.min_scale:
            raise InvalidScale("scale must be at least {}".format(self.min_scale))
        pmf = [0]
        prev = (0, 0)
        for x, fx in self.percentiles[1:]:
            limit_bucket = math.ceil(fx * scale)
            buckets = limit_bucket - len(pmf) + 1
            weight = float(x) - sum(pmf)
            while len(pmf) <= limit_bucket:
                pmf.append(weight / buckets)
        assert 0.999999 < sum(pmf) < 1.000001
        return PMF(scale, pmf)

    def cdf(self, scale=1000):
        if scale < self.min_scale:
            raise InvalidScale("scale must be at least {}".format(self.min_scale))
        pmf = self.pmf(scale=scale)
        points = list(pmf.points)
        for idx in range(1, len(points)):
            points[idx] += points[idx - 1]
        return CDF(scale, points)

class PMF:

    def __init__(self, scale, points):
        self.scale = scale
        self.points = points

    def to_cdf(self):
        return CDF(self.scale, _pmf_to_cdf(self.points))

    def to_pmf(self):
        return PMF(self.scale, list(self.points))

    def percentile(self, p):
        return self.to_cdf().percentile(p)

class CDF:

    def __init__(self, scale, points):
        self.scale = scale
        self.points = points

    def to_cdf(self):
        return CDF(self.scale, list(self.points))

    def to_pmf(self):
        return PMF(self.scale, _cdf_to_pmf(self.points))

    def percentile(self, p):
        for idx in range(0, len(self.points)):
            if self.points[idx] >= p:
                return idx / self.scale
        return len(self.points) / self.scale

def _pmf_to_cdf(pmf):
    cdf = []
    total = 0
    for x in pmf:
        total += x
        cdf.append(total)
    if not cdf or cdf[-1] < 1.0:
        cdf.append(1.0)
    return cdf

def _cdf_to_pmf(cdf):
    pmf = []
    prev = 0
    for x in cdf:
        pmf.append(x - prev)
        prev = x
    return pmf

def _extract_percentiles(SLAs):
    percentiles = set()
    for sla in SLAs:
        for p, v in sla.percentiles:
            if p > 0:
                percentiles.add(p)
    return sorted(percentiles)

def combine_in_series(*SLAs, scale=1000):
    percentiles = _extract_percentiles(SLAs)
    pmfs = [sla.pmf(scale=scale) for sla in SLAs]
    points = pmfs[0].points
    for p in pmfs[1:]:
        points = list(scipy.signal.fftconvolve(points, p.points))
    return SLA.from_pmf(PMF(scale, points), *percentiles)

# TODO(rescrv): combine_in_parallel

CONTEXT = {
    'SLA': SLA,
    'combine_in_series': combine_in_series,
}
