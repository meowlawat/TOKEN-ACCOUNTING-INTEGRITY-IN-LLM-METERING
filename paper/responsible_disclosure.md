# Responsible Disclosure

## Summary

This project produced **no new vulnerability findings against any third-party, live,
or production system.** All experiments ran exclusively against the locally-built,
vulnerable-by-construction testbed. There is therefore nothing to disclose to an
external vendor as a result of our own testing.

## Use of existing public artifacts

The study *references* already-public engineering artifacts as prior evidence that the
studied mechanisms are real. These were public before this work and are not our
findings:

- **new-api #5235** (QuantumNous/new-api) — a public GitHub issue describing a
  refund-on-missing-final-usage behavior after client disconnect. Cited as prior
  evidence for M1. We did not test new-api; we reproduced the *pattern* in our own
  testbed.
- **aperture #247** (lightninglabs/aperture) — a public PR mitigating encoding-induced
  silent zero-debit. Cited as prior evidence for M2.
- **CVE-2026-31873** (Tyk) — a public CVE for the quota-decrement race (B0).

## If real-world findings arise later

Should any future extension test a system we are authorized to test and uncover a
previously-unknown flaw, we will follow coordinated disclosure: private report to the
vendor, a reasonable remediation window (e.g. 90 days) before any public detail, and a
disclosure appendix added here recording dates and the vendor's response. No such
finding exists at this time.

## Ethics posture

Defensive research: every attack in the artifact is paired with a defense and a safety
invariant. The testbed and harness are released so defenders can reproduce and test
their own gateways; the harness targets `localhost` by default and contains no
third-party endpoints.
