| formal configuration | model-checked outcome | measured outcome |
|---|---|---|
| b0 vulnerable | Conservation (trace 21) | leak grows with concurrency: slope 0.099/request, R^2=1.0000 |
| b0 hardened | all four hold | $0 leak at every tested concurrency (1..50) |
| m1 post completion | Integrity (trace 7) | leak = value of tokens delivered before the commit; request-ASR 1.000 |
| m1 reserve refund on abort | Integrity, Refund bnd (trace 7) | leak > 0 at every abort position; invariant violated |
| m1 no reserve settle | Solvency (trace 12) | accounting integrity holds; final balance goes NEGATIVE |
| m1 reserve reconcile | all four hold | $0 leak, 0 invariant violations, balance never negative |
| m2 client | Integrity, Refund bnd (trace 8) | leakage efficiency 0.583 (prompt A) / 0.595 (prompt B) |
| m2 server recount | all four hold | leakage efficiency 0.000 across every manipulation |
| all defenses | all four hold | 16/16 regression checks; 60 cross-validation cells agree |
| all defenses 3req | all four hold | no configuration produced a violation |
