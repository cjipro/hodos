# Hodos

Hodos is an open-source engine for customer-journey intelligence — signal
harvesting, taxonomy, inference, a CHRONICLE-style evidence ledger, and
publishing/chat layers for turning raw customer signal into decisions.

**Status: pre-engine, legibility-first.** This repository currently holds
the project's legal and governance scaffolding — license, trademark
policy, contribution process, governance model, and the CJI/Hodos naming
boundary — ahead of the engine code itself. The engine is being distilled
out of a private, working application ([CJI](https://cjipro.com)) as its
patterns stabilise; extraction is in progress, not finished. If you're
looking for a runnable engine today, it isn't here yet — this repo is the
honest starting point, not a finished product wearing a README.

Why publish scaffolding before code: license and trademark terms should
exist *before* code lands, not be retrofitted once contributors show up.

## What Hodos is

The general framework: methods for making customer-journey friction
legible, wherever the customer journey happens to be. No industry lock-in,
no brand, no specific customer.

## What Hodos isn't

Hodos isn't CJI. [CJI](https://cjipro.com) is a closed, commercial product
— initially UK retail banking — built on top of Hodos, adding a curated
CHRONICLE of real-world incidents, a brand surface, and partner contracts.
None of that lives here. See [HODOS_NAMING.md](HODOS_NAMING.md) for the
full boundary.

## Documents in this repository

| File | What it covers |
|---|---|
| [LICENSE](LICENSE) | Apache License 2.0 — the code license |
| [NOTICE](NOTICE) | Copyright + trademark notice |
| [TRADEMARK.md](TRADEMARK.md) | What you can and can't do with the Hodos name |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute, DCO sign-off |
| [GOVERNANCE.md](GOVERNANCE.md) | How decisions get made, release cadence |
| [HODOS_NAMING.md](HODOS_NAMING.md) | The CJI/Hodos boundary, in full |

## Maintainer

Hussain Ahmed — hello@cjipro.com. See [GOVERNANCE.md](GOVERNANCE.md).
