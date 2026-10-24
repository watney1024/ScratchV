"""Deliberately buggy target for the AI review inline-comment smoke."""


def last_item(items):
    """Return the last element; the index is intentionally off by one."""
    return items[len(items)]


def average(total, count):
    """Average without a zero check; the smoke expects a blocker here."""
    return total / count
