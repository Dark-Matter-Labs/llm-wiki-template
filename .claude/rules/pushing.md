# Push once: the checks cost money

Agreed with Gurden on 26 October 2026. Every job on GitHub costs at least one minute. The wikis used about
25,000 minutes a month against 3,000 included. Half of the proposals were pushed twice, and 43% of the failed
checks were generated files nobody regenerated.

Before you push a draft:

1. Run `python3 tools/wiki_context.py` and `python3 tools/sync_log_index.py`.
2. Run `python3 tools/sync_index_counts.py` if this wiki has it.
3. Run `python3 tools/gates.py`. It runs this wiki's own checks here, for free.
4. Fix what it reports, then commit all of the work.
5. Push once, and open the proposal.

Push again only to fix what the checks found on GitHub. Do not push work in progress to an open proposal.
Never re-run a check by hand to see it pass. Save shared changes for the weekly rollout unless they are urgent.
