# ruff: noqa: E501
VALID_LLM_RESPONSE = """
{
    "title": "Integration Tests Setup",
    "summary": "Discussed the implementation of pytest fixtures. Need to isolate the DB and file system.",
    "action_points": [
        "Install pytest and fakeredis",
        "Write conftest.py",
        "Mock Obsidian paths"
    ],
    "tags": ["development", "testing"]
}
"""

MINIMAL_LLM_RESPONSE = """
{
    "title": "Quick Idea",
    "summary": "We should use fakeredis to prevent wiping the dev database.",
    "action_points": [],
    "tags": []
}
"""

FAKE_AUDIO_BYTES = b"RIFF....WAVEfmt ...fake_audio_data_for_whisper"
