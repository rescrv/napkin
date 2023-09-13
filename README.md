napkin
======

Napkin is a tool for doing back-of-the-envelope calculations in the style of Python.

Concretely, a napkin listing specs for i3.metal machines looks like this:

    MACHINE_CPUS = 72
    MACHINE_MEMORY = 512 * Gi # bytes
    MACHINE_NUM_DISKS = 8
    MACHINE_STORAGE = MACHINE_NUM_DISKS * 1900 * Gi # bytes
    MACHINE_NET_RATE = 10 * 1024**3 / 8 # bytes/sec
    MACHINE_IOP_SIZE = 4096 # bytes
    MACHINE_IOPS_RAND_READ = MACHINE_NUM_DISKS * 3.3 * M
    MACHINE_IOPS_SEQ_WRITE = MACHINE_NUM_DISKS * 1.4 * M

When rendered with napkin, the calculations get performed and substituted in for values.  Our annotations on each line
list the units that napkin will render.

    MACHINE_CPUS = 72
    MACHINE_MEMORY = 512GiB
    MACHINE_NUM_DISKS = 8
    MACHINE_STORAGE = 14.8TiB
    MACHINE_NET_RATE = 1.2GiB/s
    MACHINE_IOP_SIZE = 4kiB
    MACHINE_IOPS_RAND_READ = 26.4M
    MACHINE_IOPS_SEQ_WRITE = 11.2M

Napkin IS Python.  It uses the 2to3 library to transform any UPPERCASE_VARIABLE into its substituted form.

Latency Estimation
------------------

Napkin has some in-built primitives for handling latency estimates.  It is possible to define a service level objective
(SLO) and then compute the latency of sequential SLOs.

    # Our service sla specified at the 50%, 75%, 95%, 99% and 100% percentiles.
    OUR_SLO = SLO((.5, .002), (.75, .003), (.95, 0.010), (.99, 0.050), (1.0, 1.)) # percentiles:seconds
    
    TWO_OPS_IN_SERIES = combine_in_series(OUR_SLO, OUR_SLO, scale=5000) # percentiles:seconds

The output of an SLO looks like this:

    # Our service sla specified at the 50%, 75%, 95%, 99% and 100% percentiles.
    OUR_SLO = SLO((0.5, 2ms), (0.75, 3ms), (0.95, 10ms), (0.99, 50ms), (1.0, 1s))
    
    TWO_OPS_IN_SERIES = SLO((0.5, 5ms), (0.75, 9ms999µs999ns), (0.95, 38ms999µs999ns), (0.99, 528ms), (1.0, 2s))

Warts and Such
--------------

- Latency estimation doesn't do operations in series (yet).
- Variables cannot be redefined.
