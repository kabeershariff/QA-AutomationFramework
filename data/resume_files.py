"""Synthetic resume files for upload-validation tests.

The application stores resume *metadata only* — name, MIME type, size, last-modified —
and never the bytes. These fixtures exist so the suite can assert what the application
*accepts* and *rejects* without shipping a real document.
"""

from __future__ import annotations

from pathlib import Path

#: A minimal, valid PDF header. Enough for an accepted upload.
PDF_BYTES = b"%PDF-1.4\n% synthetic fixture, not a real document\n%%EOF\n"

#: Minimal PE/MZ header — a Windows executable.
EXE_BYTES = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"

RESUME_NAME = "resume.pdf"
EXE_NAME = "resume.exe"


def write_resume(directory: Path, name: str = RESUME_NAME, content: bytes = PDF_BYTES) -> str:
    """Write a resume fixture and return its path as a string."""
    path = Path(directory) / name
    path.write_bytes(content)
    return str(path)


def write_disallowed_resume(directory: Path, name: str = EXE_NAME, content: bytes = EXE_BYTES) -> str:
    """Write a file whose extension is outside the input's declared ``accept`` list."""
    return write_resume(directory, name, content)


def write_empty_resume(directory: Path, name: str = "empty.pdf") -> str:
    """Write a zero-byte resume — the right extension but no content."""
    return write_resume(directory, name, b"")