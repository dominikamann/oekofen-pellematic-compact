"""Regression: every annotation in migration.py must actually resolve.

Python 3.14 (PEP 649) evaluates annotations lazily, so a missing typing import
goes unnoticed there. On the Python versions older supported Home Assistant
releases run (hacs.json declares HA >= 2022.11.0 → Python 3.10), annotations
are evaluated eagerly at def time and an unresolvable name makes the whole
module fail to import — taking the integration down with it.

``get_type_hints`` forces the same evaluation on any Python version.
"""

from typing import get_type_hints

from custom_components.oekofen_pellematic_compact import migration


def test_module_level_function_annotations_resolve():
    unresolvable = {}
    for name in dir(migration):
        obj = getattr(migration, name)
        if not callable(obj) or getattr(obj, "__module__", None) != migration.__name__:
            continue
        try:
            get_type_hints(obj)
        except NameError as err:
            unresolvable[name] = str(err)

    assert not unresolvable, (
        f"Unresolvable annotations in migration.py: {unresolvable}. "
        f"Add the missing import — this breaks module import on Python <= 3.13."
    )
