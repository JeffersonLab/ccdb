# Conceptual design

The [database tables](database-schema.md) express objects and relations among components in the
problem space being addressed: that of developing, applying, and modifying calibration constants for
the various detector components.

There are several times associated with any set of data. One of them is the time that the data was
taken. The others are the various times at which they were calibrated (more precisely, times at which
a declaration is made about which constants should be used for a given set of data). The latter may
happen many times. Only this latter meaning is relevant for this database discussion. The time that
the data was taken is irrelevant. In this sense data may be "calibrated" (have constants assigned)
even before they are taken.

Reconstruction programs will want to fetch constants from the database by specifying the relevant
run, and the type of constants needed, by name. As a toy example, to fulfill this function we can
create a table as a join of the assignments, runRanges, constantSets, directories, and typeTables
tables. The following table can be formed unambiguously for each row of the assignment table:

    directories.name
    typeTables.name
    runRanges.runMin
    runRanges.runMax
    assignment.constantSetId

For a given type of constant set, specified by directory (`directories.name`) and type name
(`typeTables.name`), there is a run range of applicability (`runRanges.runMin` and `runMax`) and an
associated set of constants (specified by primary key, `assignment.constantSetId`). This minimal
table would suffice for this application, but it has several disadvantages. Only one set of
calibration constants for a given run can exist at one time; alternate versions are not supported. The
changes made to the constants are lost and thus reconstruction done in the past with old constants
cannot be reproduced. The run ranges must be non-overlapping or ambiguities about which constants
should be supplied would arise.

For the next step we add the time of constant set assignment:

    directories.name
    typeTables.name
    runRanges.runMin
    runRanges.runMax
    assignment.constantSetId
    assignment.created

Now with the addition of the assignment time (`assignment.created`) the run range data can specify
overlapping ranges. In case of overlap the constants that go with the most recent time are taken. If
we also never delete old assignments, this practice also provides a history mechanism: constant set
assignments that were valid at any given time can be reproduced by only accepting rows that existed
before that time. In this way the state of the table at previous times is preserved and can be
accessed.

Finally, we add another column marking a variation of the assignments:

    directories.name
    typeTables.name
    runRanges.runMin
    runRanges.runMax
    assignment.constantSetId
    assignment.created
    variations.id

Now constant sets are assigned only for particular variations, where the variations are in a
hierarchy expressed in the variations table. Each variation will typically only deal with a relatively
small number of constant set assignments. If runs or constant types are requested of a variation that
are not assigned within that variation, then the parent variation is queried, recursively, until a
valid constant set assignment is found.

> Continue with [Concepts illustrated](concepts.md) for a hands-on tour of namepaths, table types,
> assignments, and requests.
