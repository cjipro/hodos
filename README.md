# Hodos

Hodos is an open-source engine for customer-journey intelligence — signal
harvesting, taxonomy, inference, a CHRONICLE-style evidence ledger, and
publishing/chat layers for turning raw customer signal into decisions.

**Status: early — one module extracted so far.** This repository started
as legal/governance scaffolding (license, trademark policy, contribution
process, governance model) ahead of any code, and now carries its first
real piece: `hodos.publish`, a pluggable-destination abstraction extracted
from a private production system that has used it to push daily rendered
output to GitHub Pages since 2026-04. The engine is being distilled out of
that private, working application ([CJI](https://cjipro.com)) module by
module as patterns stabilise — most of the engine isn't extracted yet.
Don't expect a full framework here today; expect one tested, runnable
piece, with more following the same pattern.

## Quickstart

```bash
pip install -e ".[dev]"
pytest                        # 8 tests, no network required
python examples/local_publish.py   # writes ./published/demo/index.html
```

`hodos.publish` gives you `NullAdapter` (dry runs), `LocalAdapter` (write
to disk), and `GitHubPagesAdapter` (clone/write/commit/push to a Pages
branch) behind one `PublishAdapter` interface, so code that renders
content never needs to know where it's going. See
[`src/hodos/publish/adapters.py`](src/hodos/publish/adapters.py) for the
full interface and [`examples/local_publish.py`](examples/local_publish.py)
for a working example.

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
