---
type: is
id: is-01m5tjktdcqb25ayfnxdq3ydxa
title: "Plain scalar ending in ':' inside a flow collection: ruamel keeps the colon in the string, the yaml package reads a key"
kind: bug
status: closed
priority: 1
version: 2
labels:
  - pr-64
dependencies: []
created_at: 2026-10-25T22:24:03.500Z
updated_at: 2026-10-25T23:11:09.303Z
closed_at: 2026-10-25T23:11:09.303Z
close_reason: "Fixed in da64537 (PR #64, head ef45250): inside a flow collection both runtimes refuse, as yaml_parse_error, a ':' with no space after it before , ] } [ { ([a:, b], {a:, b}, [a :, b], {k: v:}, [\"a\":1]), a '?' glued to the next entry ([?a]), a bare '-', a leading ':' in a flow mapping, and anywhere a '#' right after a closing quote or bracket; a collection key no longer crashes Python (yaml_non_string_key). Sweep: 150,000 flow-indicator cases plus 60,000 contextual scalars, 0 silent and 0 loud differences (py C-first, pure, TS); 2,757 both-reject cases differ only in kind, documented in the spec. 22 vectors; spec + CHANGELOG. CI run 40243372151 19/19. Addendum: https://github.com/jlevy/softschema/pull/64#issuecomment-6404713010"
resolution: null
duplicate_of: null
---
Found by the number-form sweep for PR #64 (ss-j8y2), not a number issue. In a flow collection a ':' immediately followed by a flow indicator (, ] } [ {) is part of a plain scalar to ruamel and a value indicator to the yaml package (YAML 1.2). Silent differences (both valid, different values; C-first == pure): [a:, b] -> py ['a:', 'b'] / ts [{a: null}, 'b']; [a:] -> ['a:'] / [{a: null}]; {a:, b} -> {'a:': null, b: null} / {a: null, b: null}; [a :, b] -> ['a :', 'b'] / [{a: null}, 'b']; [a::, b] -> ['a::', 'b'] / [{'a:': null}, 'b']. Loud: {k: v:} (py 'v:', ts parse error), [a:[b]] and ["a":, b] (py parse error, ts reads a pair). 190 of 60,000 contextual sweep cases, all of this shape. Candidate rule: refuse, in both runtimes, a plain scalar in flow context that ends with ':' (Python: plain ScalarEvent at flow depth > 0 whose value ends with ':') and, in TS, a flow-collection value indicator ':' immediately followed by , ] } (or by [ { after a plain key); JSON's {"a":[1]} must stay accepted. Also loud and pre-existing: a bare '-' in a flow collection ([-, x]) is the string '-' to ruamel and a parse error to yaml.
