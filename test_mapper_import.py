#!/usr/bin/env python
"""Test script to verify mapper import works."""

try:
    from app.features.jobs.services.mapper import map_job_to_list_item

    print("✓ Import successful: mapper module can be imported")
    print("✓ No NameError for 'Any' type")
except NameError as e:
    print(f"✗ NameError occurred: {e}")
    exit(1)
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    exit(1)

print("✓ All checks passed!")
