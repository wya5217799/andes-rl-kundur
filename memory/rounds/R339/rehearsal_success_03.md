# R339 rehearsal 03 - sixteen-process capacity canary

- Seal: `input_bridge_seal_v3.json`
- Seal SHA-256: `4304d4fef53e62fbbac9ddf8f8d654af7ab551e94f19c889cfda2b335ab027d0`
- Distinct per-channel jobs: 16
- Unique Python processes: 16
- Native numerical threads per process: 1
- Combined operating points: 2
- Maximum worker resident set: 171932 KiB
- Sum of worker CPU time: 21.238701 s
- Overlap wall time: 2.244029 s
- Formal output created: false
- Retained scratch: `/mnt/e/Projects/andes-rl-kundur/tmp/andes/run_r339_input_bridge_diagnosis-20260804T123949.037297Z-292`

All sixteen jobs overlapped and completed. The split maps exactly to two
operating points, two input families, and four channels; it performs distinct
finite-difference columns rather than redundant simulations. This rehearsal
is accepted as the prospective host-capacity canary. The formal seal must be
rebuilt because this receipt and the accepted capacity evidence postdate v3.
