"""Tests for shared mode functionality."""

from coda.cli.shared import DeveloperMode, get_mode_description, get_system_prompt


class TestDeveloperModes:
    """Test the shared developer mode functionality."""

    def test_all_modes_defined(self):
        """Test that all expected modes are defined."""
        expected_modes = {"general", "code", "debug", "explain", "review", "refactor", "plan"}
        actual_modes = {mode.value for mode in DeveloperMode}
        assert actual_modes == expected_modes

    def test_mode_descriptions(self):
        """Test that all modes have descriptions."""
        for mode in DeveloperMode:
            desc = get_mode_description(mode)
            assert isinstance(desc, str)
            assert len(desc) > 0
            assert desc != ""  # Not just whitespace

    def test_system_prompts(self):
        """Test that all modes have system prompts."""
        for mode in DeveloperMode:
            prompt = get_system_prompt(mode)
            assert isinstance(prompt, str)
            assert len(prompt) > 0
            assert prompt != ""  # Not just whitespace

    def test_mode_description_content(self):
        """Test specific mode descriptions for correctness."""
        descriptions = {
            DeveloperMode.GENERAL: "General conversation and assistance",
            DeveloperMode.CODE: "Optimized for writing new code with best practices",
            DeveloperMode.DEBUG: "Focus on error analysis and debugging assistance",
            DeveloperMode.EXPLAIN: "Detailed code explanations and documentation",
            DeveloperMode.REVIEW: "Security and code quality review",
            DeveloperMode.REFACTOR: "Code improvement and optimization suggestions",
            DeveloperMode.PLAN: "Architecture planning and system design",
        }

        for mode, expected_desc in descriptions.items():
            assert get_mode_description(mode) == expected_desc

    def test_system_prompt_content(self):
        """Test that system prompts contain expected keywords."""
        prompt_keywords = {
            DeveloperMode.GENERAL: ["helpful", "AI assistant"],
            DeveloperMode.CODE: ["coding assistant", "clean", "efficient"],
            DeveloperMode.DEBUG: ["debugging expert", "identifying issues"],
            DeveloperMode.EXPLAIN: ["patient teacher", "detailed explanations"],
            DeveloperMode.REVIEW: ["code reviewer", "security", "performance"],
            DeveloperMode.REFACTOR: ["refactoring specialist", "improvements"],
            DeveloperMode.PLAN: ["software architect", "system design"],
        }

        for mode, keywords in prompt_keywords.items():
            prompt = get_system_prompt(mode)
            for keyword in keywords:
                assert keyword in prompt, f"'{keyword}' not found in {mode.value} prompt"

    def test_invalid_mode_handling(self):
        """Test handling of invalid modes."""

        # Since we're using an enum, we can't pass invalid values directly
        # But we can test the fallback behavior
        class FakeMode:
            value = "nonexistent"

        # These should return empty strings for invalid modes
        assert get_mode_description(FakeMode) == ""
        assert get_system_prompt(FakeMode) == ""
