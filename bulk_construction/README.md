Build All: Bulk Construction, One Click
=======================================

**What it does:** in the construction panel you already use -- pick a building
from the bottom bar, the "select in which State to build" list opens -- it adds
a 1 / 5 / 10 level stepper and one button that queues that building in every
state the panel is currently listing as valid.

Validate with:

    python tools/validate_syntax.py bulk_construction --strict

Package for upload with (never upload the dev junction):

    python tools/package_release.py bulk_construction
