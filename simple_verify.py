#!/usr/bin/env python
"""Simple verification that the mapper import works."""

print("Testing mapper import...")

try:
    # This should work now that we've added the import
    from app.features.jobs.services.mapper import map_job_to_list_item

    print("✅ SUCCESS: Mapper module imported without NameError!")
    print("✅ The fix is working correctly.")

    # Test that the function exists and is callable
    assert callable(map_job_to_list_item)
    print("✅ Mapper function is callable.")

    print("\n🎉 All checks passed! The NameError has been resolved.")

except NameError as e:
    print(f"❌ FAILED: NameError still occurs: {e}")
    exit(1)
except Exception as e:
    print(f"❌ FAILED: Unexpected error: {e}")
    exit(1)
