---
id: CLM-NNNN
type: finding          # finding | decision | correction
trust: V               # V (verified) | S (stated) | T (theoretical)
                       # Note: decision MUST be S; correction MUST be V
status: current        # current | superseded | obsoleted
statement: |
  <one paragraph; cite specific numbers, configs, claim IDs>
round: R<N>
provenance:
  - <path/to/result.json>  # K will WARN if missing on disk
  - <path/to/script.py>
  - memory/rounds/R<N>/verdict.md
tags: [<key>, <words>, <for-query>]
# Optional structured metric block — fill in if statement cites a
# benchmark number. Enables STATE.md ## Leaderboard (R50 H) and
# `query.py --best <metric_name>` lookups (R50 L).
# metric:
#   name: 6_axis      # or settling_s, max_df_Hz, etc.
#   value: 0.334      # numeric, NOT bool
# Optional supersede chain (if this claim replaces an older one).
# supersedes: [CLM-XXXX]
# Optional obsoletion (if external change rendered the claim stale
# WITHOUT a successor — e.g. ranker drift).
# obsoleted_round: R<N>
# obsoleted_reason: <one sentence>
---
