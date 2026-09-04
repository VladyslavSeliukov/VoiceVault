from typing import Any

import httpx
import pytest
from pydantic import BaseModel

from core.exceptions import LLMProcessingError
from modules.llm.client import (
    _call_llm,
    analyze_transcript,
    extract_structured_data,
    generate_rag_response,
)
from modules.llm.schemas import NoteAnalysis

pytestmark = pytest.mark.asyncio


class TestLowLevelLLMCall:
    """Tests for the underlying HTTP client interactions with the local Ollama."""

    async def test_call_llm_success(self, mocker: Any) -> None:
        """Verifies successful HTTP requests return formatted message payloads."""
        mock_response: Any = mocker.Mock(spec=httpx.Response)
        mock_response.json.return_value = {
            "message": {"content": "Hello", "reasoning_content": "Thinking"}
        }
        mock_response.raise_for_status = mocker.Mock()

        mock_client: Any = mocker.AsyncMock()
        mock_client.post.return_value = mock_response

        mocker.patch(
            "modules.llm.client.httpx.AsyncClient.__aenter__", return_value=mock_client
        )

        result: dict[str, Any] = await _call_llm("sys", "user")

        assert result["content"] == "Hello"
        assert result["reasoning_content"] == "Thinking"
        assert result["raw_message"] == {
            "content": "Hello",
            "reasoning_content": "Thinking",
        }

    async def test_call_llm_http_error(self, mocker: Any) -> None:
        """Verifies HTTP status errors are wrapped into LLMProcessingError."""
        mock_response: Any = mocker.Mock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=mocker.Mock(), response=mocker.Mock()
        )

        mock_client: Any = mocker.AsyncMock()
        mock_client.post.return_value = mock_response
        mocker.patch(
            "modules.llm.client.httpx.AsyncClient.__aenter__", return_value=mock_client
        )

        with pytest.raises(LLMProcessingError, match="error status code"):
            await _call_llm("sys", "user")

    async def test_call_llm_network_error(self, mocker: Any) -> None:
        """Verifies connection timeouts and network failures raise LLMProcessingError"""
        mock_client: Any = mocker.AsyncMock()
        mock_client.post.side_effect = httpx.RequestError(
            "Network Error", request=mocker.Mock()
        )
        mocker.patch(
            "modules.llm.client.httpx.AsyncClient.__aenter__", return_value=mock_client
        )

        with pytest.raises(LLMProcessingError, match="Network issue"):
            await _call_llm("sys", "user")

    async def test_call_llm_parsing_error(self, mocker: Any) -> None:
        """Verifies malformed JSON responses are gracefully caught and wrapped."""
        mock_response: Any = mocker.Mock(spec=httpx.Response)
        mock_response.raise_for_status = mocker.Mock()
        mock_response.json.side_effect = KeyError("Simulated KeyError")

        mock_client: Any = mocker.AsyncMock()
        mock_client.post.return_value = mock_response
        mocker.patch(
            "modules.llm.client.httpx.AsyncClient.__aenter__", return_value=mock_client
        )

        with pytest.raises(
            LLMProcessingError, match="Malformed API response structure"
        ):
            await _call_llm("sys", "user")


class DummySchema(BaseModel):
    """Dummy Pydantic schema for testing structured extraction."""

    title: str


class TestStructuredDataExtraction:
    """Tests for parsing and validating LLM outputs against Pydantic schemas."""

    async def test_extract_structured_data_success(self, mocker: Any) -> None:
        """Verifies correct parsing of payloads, including stripping markdown blocks."""
        mock_call: Any = mocker.patch(
            "modules.llm.client._call_llm", new_callable=mocker.AsyncMock
        )
        mock_call.return_value = {
            "content": '```json\n{"title": "Valid Title"}\n```',
            "reasoning_content": "",
        }

        result: DummySchema = await extract_structured_data(
            "text", DummySchema, "{schema}", []
        )
        assert isinstance(result, DummySchema)
        assert result.title == "Valid Title"

    async def test_extract_structured_data_fallback_to_reasoning(
        self, mocker: Any
    ) -> None:
        """Verify fallback to reasoning content when primary content is empty."""
        mock_call: Any = mocker.patch(
            "modules.llm.client._call_llm", new_callable=mocker.AsyncMock
        )
        mock_call.return_value = {
            "content": "",
            "reasoning_content": '{"title": "Reasoning Title"}',
        }

        result: DummySchema = await extract_structured_data(
            "text", DummySchema, "{schema}", []
        )
        assert result.title == "Reasoning Title"

    async def test_extract_structured_data_empty_response(self, mocker: Any) -> None:
        """Verify LLMProcessingError is raised on empty LLM responses."""
        mock_call: Any = mocker.patch(
            "modules.llm.client._call_llm", new_callable=mocker.AsyncMock
        )
        mock_call.return_value = {"content": "   ", "reasoning_content": "\n"}

        with pytest.raises(LLMProcessingError, match="absolutely empty response"):
            await extract_structured_data("text", DummySchema, "{schema}", [])

    async def test_extract_structured_data_validation_error(self, mocker: Any) -> None:
        """Verifies Pydantic validation failures raise LLMProcessingError."""
        mock_call: Any = mocker.patch(
            "modules.llm.client._call_llm", new_callable=mocker.AsyncMock
        )
        mock_call.return_value = {
            "content": '{"wrong_field": 123}',
            "reasoning_content": "",
        }

        with pytest.raises(
            LLMProcessingError, match="Failed to validate structured data"
        ):
            await extract_structured_data("text", DummySchema, "{schema}", [])


class TestDomainWrappers:
    """Test high-level business wrappers for the LLM pipeline."""

    async def test_analyze_transcript_calls_extractor(self, mocker: Any) -> None:
        """Verify transcript analysis delegates to structured extractor."""
        mock_extract: Any = mocker.patch(
            "modules.llm.client.extract_structured_data", new_callable=mocker.AsyncMock
        )
        mock_extract.return_value = NoteAnalysis(
            title="A", summary="B", action_points=[], tags=[]
        )

        result: NoteAnalysis = await analyze_transcript("my text", ["tag1"])

        assert result.title == "A"
        mock_extract.assert_called_once()
        assert mock_extract.call_args.kwargs["user_text"] == "my text"
        assert mock_extract.call_args.kwargs["allowed_tags"] == ["tag1"]

    async def test_generate_rag_response_success(self, mocker: Any) -> None:
        """Verifies successful RAG response generation."""
        mock_call: Any = mocker.patch(
            "modules.llm.client._call_llm", new_callable=mocker.AsyncMock
        )
        mock_call.return_value = {"content": "RAG Answer", "reasoning_content": ""}

        result: str = await generate_rag_response("Query", "Context")
        assert result == "RAG Answer"

    async def test_generate_rag_response_fallback(self, mocker: Any) -> None:
        """Verify RAG fallback to reasoning content on empty response."""
        mock_call: Any = mocker.patch(
            "modules.llm.client._call_llm", new_callable=mocker.AsyncMock
        )
        mock_call.return_value = {
            "content": "  ",
            "reasoning_content": "Deep thought answer",
        }

        result: str = await generate_rag_response("Query", "Context")
        assert result == "Deep thought answer"

    async def test_generate_rag_response_empty(self, mocker: Any) -> None:
        """Verify safe fallback returned when LLM text generation fails."""
        mock_call: Any = mocker.patch(
            "modules.llm.client._call_llm", new_callable=mocker.AsyncMock
        )
        mock_call.return_value = {"content": "", "reasoning_content": ""}

        result: str = await generate_rag_response("Query", "Context")
        assert result == "❌ LLM failed to generate a response."
