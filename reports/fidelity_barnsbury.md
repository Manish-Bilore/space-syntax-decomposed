# Fidelity report: barnsbury

Our reimplementation vs depthmapX (reference). Our code is fed depthmapX's exported
connection lists, so differences are in measure definitions, not graph construction.
`share_within_tol` = share of features with relative error <= 1e-5.

## Axial map (1100 lines, 9 components)

| measure               |    n |   share_within_tol |   max_rel_err |   spearman |
|:----------------------|-----:|-------------------:|--------------:|-----------:|
| Connectivity          | 1100 |           1        |   0           |   1        |
| Control               | 1092 |           1        |   8e-08       |   0.999998 |
| Controllability       | 1092 |           1        |   9.2e-08     |   1        |
| Node Count            | 1100 |           1        |   0           |   1        |
| Total Depth           | 1092 |           1        |   0           |   1        |
| Mean Depth            | 1092 |           1        |   6.84197e-08 |   1        |
| RA                    | 1092 |           1        |   8.18653e-08 |   1        |
| RRA                   | 1092 |           1        |   9.28939e-08 |   1        |
| Integration [HH]      | 1092 |           1        |   1.05226e-07 |   1        |
| Integration [P-value] | 1092 |           1        |   8.52701e-08 |   1        |
| Integration [Tekl]    | 1092 |           1        |   4.86087e-08 |   1        |
| Integration [HH] R3   | 1092 |           1        |   8.57737e-08 |   1        |
| Choice                | 1092 |           0.165751 |   1e+12       |   0.995762 |
| Choice R3             | 1092 |           0.227106 |   7.25238e+12 |   0.993955 |

- Choice total (sum over all lines): ours 7.47591e+06, depthmapX 7.47591e+06.
- depthmapX breaks ties between equal-length routes at random, so its axial choice varies between runs: two random-tie runs correlate at Spearman 0.9946. Ours splits ties equally (deterministic).
- Intelligibility r = 0.535 (r^2 = 0.287); synergy r = 0.721.

## Segment map, angular tulip-1024 (5459 segments)

| radius   | measure                         |    n |   share_within_tol |   max_rel_err |   spearman |
|:---------|:--------------------------------|-----:|-------------------:|--------------:|-----------:|
| R400     | Node Count                      | 5459 |           1        |   0           |   1        |
| R400     | Total Depth                     | 5458 |           1        |   4.99298e-08 |   1        |
| R400     | Integration                     | 5458 |           1        |   7.8125e-08  |   1        |
| R400     | Choice (depthmapX rule)         | 5459 |           1        |   0           |   1        |
| R400     | Choice (clean rule)             | 5459 |           0.414178 |   0.931818    |   0.999311 |
| R400     | Choice total: clean / depthmapX | 5459 |         nan        | nan           |   1.07107  |
| R800     | Node Count                      | 5459 |           1        |   0           |   1        |
| R800     | Total Depth                     | 5459 |           1        |   4.99984e-08 |   1        |
| R800     | Integration                     | 5459 |           1        |   9.35768e-08 |   1        |
| R800     | Choice (depthmapX rule)         | 5459 |           0.995787 |   0.0381289   |   1        |
| R800     | Choice (clean rule)             | 5459 |           0.401172 |   0.60375     |   0.99977  |
| R800     | Choice total: clean / depthmapX | 5459 |         nan        | nan           |   1.02493  |
| R1200    | Node Count                      | 5459 |           1        |   0           |   1        |
| R1200    | Total Depth                     | 5459 |           0.999817 |   6.7114e-05  |   1        |
| R1200    | Integration                     | 5459 |           0.999817 |   6.71383e-05 |   1        |
| R1200    | Choice (depthmapX rule)         | 5459 |           0.99139  |   0.0137646   |   1        |
| R1200    | Choice (clean rule)             | 5459 |           0.398608 |   0.484576    |   0.99985  |
| R1200    | Choice total: clean / depthmapX | 5459 |         nan        | nan           |   0.997819 |
| Rn       | Node Count                      | 5459 |           1        |   0           | nan        |
| Rn       | Total Depth                     | 5459 |           1        |   2.63514e-08 |   1        |
| Rn       | Integration                     | 5459 |           1        |   1.0398e-07  |   1        |
| Rn       | Choice (depthmapX rule)         | 5459 |           0.996703 |   0.00436859  |   1        |
| Rn       | Choice (clean rule)             | 5459 |           0.397875 |   0.412401    |   0.999744 |
| Rn       | Choice total: clean / depthmapX | 5459 |         nan        | nan           |   0.899381 |

- 'Choice (depthmapX rule)' reproduces depthmapX's per-direction counting; 'clean rule' counts each origin-destination segment pair once. The total ratio row shows how much depthmapX's convention inflates choice.
- Reimplementation time per radius (s, both rules): {'R400': 4.2, 'R800': 16.9, 'R1200': 41.9, 'Rn': 527.4}
