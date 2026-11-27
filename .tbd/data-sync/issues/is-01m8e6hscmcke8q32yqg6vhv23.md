---
type: is
id: is-01m8e6hscmcke8q32yqg6vhv23
title: Investigate shared-host sensitivity in parser growth timing probes
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-11-27T09:49:26.288Z
updated_at: 2026-11-27T09:49:26.288Z
---
During final local validation of SoftSchema #78 at e6ee08f on macOS Python 3.14.7, make lint-check test passed lint/default tests but failed the slow comment_lines and space_only_lines timing ratios. One observed pair was small=0.0006671s, large=0.7708556s (limit 1000x). The parser and test files are unchanged from origin/main c84456d. An immediate isolated rerun of all seven growth shapes passed in 16.48s. CI full matrices for #78 and #79 both passed all 19 checks. Characterize shared-host scheduling sensitivity before changing the bound; preserve the intended ability to catch quadratic regex work.
