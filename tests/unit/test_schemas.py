import pytest
from pydantic import ValidationError

from modules.llm.schemas import NoteAnalysis
from tests.fixtures.mock_data import MINIMAL_LLM_RESPONSE, VALID_LLM_RESPONSE


class TestNoteAnalysisValidation:
    """Tests for successful Pydantic validation and parsing of LLM JSON responses."""

    def test_note_analysis_valid_parsing(self) -> None:
        """Verifies complete and valid JSON is parsed correctly."""
        note: NoteAnalysis = NoteAnalysis.model_validate_json(VALID_LLM_RESPONSE)

        assert note.title == "Integration Tests Setup"
        assert len(note.action_points) == 3
        assert note.tags == ["development", "testing"]

    def test_note_analysis_minimal_parsing(self) -> None:
        """Verifies JSON with minimal required fields is parsed correctly."""
        note: NoteAnalysis = NoteAnalysis.model_validate_json(MINIMAL_LLM_RESPONSE)

        assert note.title == "Quick Idea"
        assert note.action_points == []
        assert note.tags == []

    def test_note_analysis_extra_fields_ignored_or_allowed(self) -> None:
        """Verifies hallucinated or extra JSON fields are safely ignored."""
        json_with_extra: str = """
        {
            "title": "Test",
            "summary": "Summary",
            "action_points": [],
            "tags": [],
            "hallucinated_field": "some garbage"
        }
        """
        note: NoteAnalysis = NoteAnalysis.model_validate_json(json_with_extra)
        assert not hasattr(note, "hallucinated_field")


class TestNoteAnalysisErrorHandling:
    """Tests for schema validation failures during malformed LLM responses."""

    def test_note_analysis_missing_required_fields(self) -> None:
        """Verifies ValidationError is raised when mandatory fields are missing."""
        invalid_json: str = '{"title": "Only Title"}'

        with pytest.raises(ValidationError) as exc_info:
            NoteAnalysis.model_validate_json(invalid_json)

        assert "summary" in str(exc_info.value)

    def test_note_analysis_wrong_types(self) -> None:
        """Verifies ValidationError is raised when field types mismatch."""
        bad_json: str = """
        {
            "title": "Title",
            "summary": "Summary",
            "action_points": "Just one task as a string",
            "tags": []
        }
        """
        with pytest.raises(ValidationError) as exc_info:
            NoteAnalysis.model_validate_json(bad_json)

        assert "action_points" in str(exc_info.value)

    def test_note_analysis_explicit_null(self) -> None:
        """Verifies ValidationError is raised when a required string field is null."""
        bad_json: str = """
        {
            "title": "Title",
            "summary": null,
            "action_points": [],
            "tags": []
        }
        """
        with pytest.raises(ValidationError) as exc_info:
            NoteAnalysis.model_validate_json(bad_json)

        assert "summary" in str(exc_info.value)
        assert "Input should be a valid string" in str(exc_info.value)

    def test_note_analysis_broken_json(self) -> None:
        """Verifies ValidationError is raised for truncated or invalid JSON strings."""
        truncated_json: str = """
        {
            "title": "Title",
            "summary": "Summary",
            "action_points": [
        """
        with pytest.raises(ValidationError):
            NoteAnalysis.model_validate_json(truncated_json)

    def test_note_analysis_wrong_root_type(self) -> None:
        """Verify ValidationError is raised when JSON root is array, not object."""
        json_array: str = """
        [{
            "title": "Title",
            "summary": "Summary",
            "action_points": [],
            "tags": []
        }]
        """
        with pytest.raises(ValidationError) as exc_info:
            NoteAnalysis.model_validate_json(json_array)

        assert "Input should be an object" in str(exc_info.value)
