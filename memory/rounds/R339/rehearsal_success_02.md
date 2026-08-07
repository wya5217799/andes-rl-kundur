# R339 rehearsal 02

- Seal: `input_bridge_seal_v2.json`
- Seal SHA-256: `6e7e01c2c68d0922e467a5392705f914fb5289c289febe829f4da9adaf0981db`
- Installed case SHA-256: `f725e03ba12d8207616f68acdd606bbd35e7c4a68f13e66d7db43925adac2ed8`
- Isolated jobs: 4
- Unique Python processes: 4
- Combined operating points: 2
- Formal output created: false
- Retained scratch: `/mnt/e/Projects/andes-rl-kundur/tmp/andes/run_r339_input_bridge_diagnosis-20260804-122643-395`

The first invocation used a repository-relative seal path after the scratch
wrapper had changed directory and therefore stopped at seal lookup, before any
live job or formal artifact. Repeating the same sealed rehearsal with the
absolute WSL seal path traversed the installed runtime, case, equilibrium,
Jacobian, and finite-difference path successfully. This rehearsal predates the
later per-channel concurrency change and is retained only as chronology, not
as capacity evidence for that change.
