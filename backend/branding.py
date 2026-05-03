"""Application ownership and branding metadata."""

from __future__ import annotations


_DEVELOPER_CODEPOINTS = [
    66,
    104,
    117,
    109,
    105,
    110,
    32,
    80,
    97,
    108,
    97,
    100,
    105,
    121,
    97,
]

_PROFILE_URL_CODEPOINTS = [
    104,
    116,
    116,
    112,
    115,
    58,
    47,
    47,
    119,
    119,
    119,
    46,
    108,
    105,
    110,
    107,
    101,
    100,
    105,
    110,
    46,
    99,
    111,
    109,
    47,
    105,
    110,
    47,
    98,
    104,
    117,
    109,
    105,
    110,
    45,
    112,
    97,
    108,
    97,
    100,
    105,
    121,
    97,
]


APP_NAME = "Smart Invoice + GST Tool"
DEVELOPER_NAME = "".join(chr(codepoint) for codepoint in _DEVELOPER_CODEPOINTS)
DEVELOPER_SIGNATURE = f"Developed by {DEVELOPER_NAME}"
DEVELOPER_PROFILE_URL = "".join(chr(codepoint) for codepoint in _PROFILE_URL_CODEPOINTS)


def console_banner() -> str:
    """Return the startup banner shown in backend logs and console."""
    return f"{APP_NAME} API | {DEVELOPER_SIGNATURE}"


def branding_payload() -> dict[str, str]:
    """Return app ownership metadata for frontend display."""
    return {
        "app_name": APP_NAME,
        "developer_name": DEVELOPER_NAME,
        "developer_signature": DEVELOPER_SIGNATURE,
        "developer_profile_url": DEVELOPER_PROFILE_URL,
    }
