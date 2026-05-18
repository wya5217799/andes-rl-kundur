# §VII-C Code-drift caveat — replacement drafts

Three scenarios for the bisection outcome, depending on what
`collect.py` shows once R60..R65 land. Pick one once `score_bisect.log`
reports the topological-order numbers. Last-paragraph replacement only
— the "headline regression" / "memoryless TD3/SAC reproduce cleanly"
opening stays. Topological order is:

```
R58 e8427df  →  R60 2752a8f  →  R61 1a3a4ad  →  R62 48c466c
       →  R63 6671e8d  →  R64 6c27ae1  →  R65 4c5327a  →  R59 43d203b
```

Smoke-test already established: R58 (e8427df) and R59 (43d203b) —
the topological endpoints — give identical $v_{3.1}=0.358$, $\text{cum\_rf}=-0.069$
under the current main-worktree v3.1 ranker. Any cliff between them
must therefore be V-shaped (down then back up) on this metric.

> Note: the headline $v_{6\text{-axis}}=0.526 \to 0.426$ in CLM-0104 was
> measured under the LEGACY 6-axis ranker on s51 ckpts. Phase 3 E3
> re-trains every commit and scores under v3.1 (11-axis) to make the
> commits comparable to each other on the project's current paper
> ranker — not to reproduce the 6-axis number. The relevant signal is
> the **adjacent-pair $\Delta v_{3.1}$**, not the absolute level.

---

## Scenario A — flat (no cliff observed under v3.1)

> The candidate commit range was bisected across all eight
> commits R58 (\texttt{e8427df}) $\rightarrow$ R65 (\texttt{4c5327a})
> $\rightarrow$ R59 (\texttt{43d203b}) (Sec.~\ref{sec:phase3} E3,
> Table~\ref{tab:phase3-e3}); under the current v3.1 ranker every
> commit reproduced to within $\pm 0.0X$ of $v_{3.1} = 0.358$.
> We could therefore not localise a $\Delta v_{3.1}$ cliff to a single
> commit on the bisected range. The legacy 6-axis ranker drift
> documented in CLM-0104 may then reflect either (i) sensitivity
> specific to the 6-axis ranker, which v3.1's multiplicative gating
> dampens, or (ii) a code drift earlier than R58 that we did not
> include in the bisection range. The numbers in this paper are
> pinned to the post-regression code path. For reproducibility we
> publish (a) the git SHA of the commit producing each table
> (see \texttt{README.md}) and (b) the bit-identical regression test
> \texttt{tests/test\_v4\_env\_regression.py} that has held the V4
> environment to $10^{-9}$ tolerance against the pre-refactor
> baseline. Whether the LSTM-only $\sim$19\% 6-axis drift is a
> fundamental reproducibility limit specific to the legacy ranker
> or an unidentified bug remains open.

## Scenario B — single cliff localised to commit $C$

> The candidate commit range was bisected across all eight
> commits R58 (\texttt{e8427df}) $\rightarrow$ R65 (\texttt{4c5327a})
> $\rightarrow$ R59 (\texttt{43d203b}) (Sec.~\ref{sec:phase3} E3,
> Table~\ref{tab:phase3-e3}). Under the current v3.1 ranker the
> adjacent-pair delta exceeds 0.05 between commits R$X$ (\texttt{$SHA_a$})
> and R$Y$ (\texttt{$SHA_b$}): the former trains to
> $v_{3.1} = a$, the latter to $v_{3.1} = b$ (same seed 51, warm-up 5,
> $\tau = 0.005$). The introducing commit added $\langle$one-line
> description of the diff, e.g. ``a Python \texttt{atexit} handler
> in the training monitor''$\rangle$, which is consistent with the
> RNG-offset hypothesis: any commit that shifts the global numpy or
> torch RNG state before the LSTM hidden-state initialisation will
> propagate through the BPTT chain. The cliff disappears between R$Y$
> and R$Z$ ($v_{3.1}$ returns to $\sim 0.358$), explaining why the
> R58 and R59 endpoints under v3.1 are equivalent. The legacy 6-axis
> ranker likely amplifies the post-R$X$ drift while v3.1's
> multiplicative gating dampens it. The numbers in this paper are
> pinned to the post-regression code path; we are not back-porting
> the R$X$$\rightarrow$R$Y$ fix because the headline numbers are
> already from the post-cliff (R$Y$ onwards) state. For
> reproducibility we publish (a) the git SHA of the commit producing
> each table (see \texttt{README.md}) and (b) the bit-identical
> regression test \texttt{tests/test\_v4\_env\_regression.py} that
> has held the V4 environment to $10^{-9}$ tolerance against the
> pre-refactor baseline.

## Scenario C — multiple sub-threshold deltas, no single cliff

> The candidate commit range was bisected across all eight commits
> R58 (\texttt{e8427df}) $\rightarrow$ R65 (\texttt{4c5327a})
> $\rightarrow$ R59 (\texttt{43d203b}) (Sec.~\ref{sec:phase3} E3,
> Table~\ref{tab:phase3-e3}). Under the current v3.1 ranker every
> adjacent-pair delta stayed below 0.05 ($|\Delta v_{3.1}| \leq$ X),
> with $v_{3.1}$ drifting between $\langle\min\rangle$ and
> $\langle\max\rangle$ over the eight commits. The drift is
> therefore not attributable to a single offending commit on the
> bisected range; the cumulative trajectory of micro-changes
> (monitor extension, env-var overrides, paper-strict-eval scaffold)
> sums to the observed reproduction gap. The most likely mechanism
> remains RNG-state shift from added \texttt{os.environ.get(\dots)}
> reads and side-effecting imports before the LSTM hidden state is
> initialised, which BPTT then amplifies. The legacy 6-axis ranker
> likely amplifies this drift while v3.1's multiplicative gating
> dampens it. The numbers in this paper are pinned to the
> post-regression code path. For reproducibility we publish (a) the
> git SHA of the commit producing each table (see \texttt{README.md})
> and (b) the bit-identical regression test
> \texttt{tests/test\_v4\_env\_regression.py} that has held the V4
> environment to $10^{-9}$ tolerance against the pre-refactor
> baseline. Whether the LSTM-only drift is a fundamental
> reproducibility limit or a coordinated set of RNG-state shifts
> remains open.

---

## Table addition (all scenarios)

Add a new tbl row group under E1 in Table~\ref{tab:phase3} (or a
small separate Table~\ref{tab:phase3-e3}):

```latex
\midrule
\multicolumn{4}{l}{\emph{E3: code-drift bisection over R58$\rightarrow$R59
  (topological order, td3\_lstm s51 wu5 $\tau=$0.005)}} \\
R58 \texttt{e8427df} & baseline   & 0.358 & post-paper-strict audit \\
R60 \texttt{2752a8f} & +probes    & 0.??? & no-control scale check \\
R61 \texttt{1a3a4ad} & +monitor   & 0.??? & atexit + Q-0007 \\
R62 \texttt{48c466c} & +Q7 verify & 0.??? & --- \\
R63 \texttt{6671e8d} & +env vars  & 0.??? & N\_SUBSTEPS / MAX\_GRAD\_NORM \\
R64 \texttt{6c27ae1} & +env vars  & 0.??? & LR / EXPLORE\_NOISE \\
R65 \texttt{4c5327a} & +env var   & 0.??? & LSTM\_LR\_UNCLAMP \\
R59 \texttt{43d203b} & PI layer   & 0.358 & doc-only on training path \\
```
