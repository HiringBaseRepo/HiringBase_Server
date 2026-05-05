#!/usr/bin/env python
"""Comprehensive verification script for the fix."""

import asyncio
import sys
from typing import Any, Dict, List


def test_mapper_import():
    """Test that mapper module can be imported without NameError."""
    print("🔍 Testing mapper import...")
    try:
        from app.features.jobs.services.mapper import (
            map_form_field_to_item,
            map_job_to_list_item,
            map_knockout_rule_to_item,
            map_requirement_to_item,
        )

        print("✅ Mapper import successful - No NameError!")
        return True
    except NameError as e:
        print(f"❌ NameError occurred: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_mapper_functions():
    """Test that mapper functions work correctly."""
    print("\n🔍 Testing mapper functions...")
    try:
        from datetime import datetime

        from app.features.jobs.schemas.schema import JobListItem
        from app.features.jobs.services.mapper import map_job_to_list_item

        # Create a mock job object
        class MockJob:
            def __init__(self):
                self.id = 1
                self.title = "Test Job"
                self.department = "Engineering"
                self.employment_type = "FULL_TIME"
                self.status = "PUBLISHED"
                self.location = "Jakarta"
                self.apply_code = "TEST2024"
                self.published_at = datetime.now()
                self.created_at = datetime.now()

        mock_job = MockJob()
        result = map_job_to_list_item(mock_job)

        assert isinstance(result, JobListItem)
        assert result.title == "Test Job"
        assert result.department == "Engineering"

        print("✅ Mapper functions work correctly!")
        return True
    except Exception as e:
        print(f"❌ Mapper function test failed: {e}")
        return False


def test_ai_fallbacks():
    """Test that AI services have proper fallbacks."""
    print("\n🔍 Testing AI service fallbacks...")

    # Test LLM fallback
    try:
        from app.ai.llm.client import call_llm
        from app.core.config import settings

        # Temporarily set GROQ_API_KEY to None
        original_key = settings.GROQ_API_KEY
        settings.GROQ_API_KEY = None

        async def test_llm_fallback():
            result = await call_llm("Test prompt")
            assert result is None, "LLM should return None when API key is missing"
            print("✅ LLM fallback works correctly!")

        asyncio.run(test_llm_fallback())

        # Restore original value
        settings.GROQ_API_KEY = original_key
        return True
    except Exception as e:
        print(f"❌ LLM fallback test failed: {e}")
        return False


def test_document_validator_fallback():
    """Test document validator fallback."""
    print("\n🔍 Testing document validator fallback...")
    try:
        from app.ai.validator.document_validator import validate_document_content
        from app.core.config import settings

        # Temporarily set GROQ_API_KEY to None
        original_key = settings.GROQ_API_KEY
        settings.GROQ_API_KEY = None

        async def test_validator_fallback():
            result = await validate_document_content(
                "KTP", "Test OCR text", {"name": "Test User"}
            )
            assert result["valid"] is True
            assert "Validator skipped" in result["reason"]
            print("✅ Document validator fallback works correctly!")

        asyncio.run(test_validator_fallback())

        # Restore original value
        settings.GROQ_API_KEY = original_key
        return True
    except Exception as e:
        print(f"❌ Document validator fallback test failed: {e}")
        return False


def test_application_initialization():
    """Test that FastAPI application can initialize."""
    print("\n🔍 Testing application initialization...")
    try:
        from app.main import app

        assert app is not None
        print("✅ FastAPI application initializes successfully!")
        return True
    except Exception as e:
        print(f"❌ Application initialization failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("🚀 Starting comprehensive fix verification...\n")

    tests = [
        test_mapper_import,
        test_mapper_functions,
        test_ai_fallbacks,
        test_document_validator_fallback,
        test_application_initialization,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)

    print("\n" + "=" * 50)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 50)

    passed = sum(results)
    total = len(results)

    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("🎉 ALL TESTS PASSED! The fix is working correctly.")
        print("\n📝 Next steps:")
        print("1. Run full test suite: venv/bin/pytest app/tests/ -v")
        print("2. Run integration tests: venv/bin/pytest app/tests/integration/ -v")
        print("3. Check test coverage with: venv/bin/pytest --cov=app tests/")
        return 0
    else:
        print("❌ Some tests failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
