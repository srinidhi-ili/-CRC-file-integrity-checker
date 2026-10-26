"""
crc_core.py
Core logic for the CRC-32 File Integrity Checker.

Implements:
- Week 1 workflow: read bytes -> calculate CRC-32 -> store reference ->
  recalculate later -> compare -> VALID / CORRUPTED -> save report
- Week 3 workflow: 8 error simulation methods used to test the checker
"""

import zlib
import os
import json
import random
from datetime import datetime

REFERENCE_STORE = "reference_crc.json"
REPORT_FILE = "verification_report.txt"


# ============================================================
# WEEK 1 CORE WORKFLOW
# ============================================================

def read_file_as_bytes(filepath):
    """Read the data as bytes. Works identically for TXT, CSV, PDF,
    DOCX, ZIP, images -- anything -- because binary mode never
    interprets content, it just reads raw bytes."""
    with open(filepath, "rb") as f:
        return f.read()


def calculate_crc32(data_bytes):
    """Calculate CRC-32 checksum of the given bytes."""
    return format(zlib.crc32(data_bytes) & 0xFFFFFFFF, "08x")


def _load_store():
    if os.path.exists(REFERENCE_STORE):
        with open(REFERENCE_STORE, "r") as f:
            return json.load(f)
    return {}


def store_reference_crc(filepath):
    """Store the reference CRC for a file. This is the 'baseline'
    fingerprint we compare against later."""
    data = read_file_as_bytes(filepath)
    crc_value = calculate_crc32(data)

    store = _load_store()
    store[os.path.abspath(filepath)] = {
        "crc": crc_value,
        "stored_at": datetime.now().isoformat(timespec="seconds"),
    }
    with open(REFERENCE_STORE, "w") as f:
        json.dump(store, f, indent=2)

    print(f"[STORED] Reference CRC for '{filepath}': {crc_value}")
    return crc_value


def calculate_current_crc(filepath):
    """Calculate the current CRC-32 of a file as it exists right now."""
    data = read_file_as_bytes(filepath)
    return calculate_crc32(data)


def verify_file(filepath, method_name="Direct check (no simulation)"):
    """Compare current CRC against the stored reference CRC.
    This is the decision point: 'Do current and reference CRC values match?'"""
    store = _load_store()
    key = os.path.abspath(filepath)

    if key not in store:
        print(f"[ERROR] No reference CRC found for '{filepath}'. "
              f"Store a reference first (option 2 in the menu).")
        return None

    reference_crc = store[key]["crc"]
    current_crc = calculate_current_crc(filepath)

    match = (current_crc == reference_crc)
    status = "VALID" if match else "CORRUPTED"
    label = ("CRC unchanged -- No content change detected" if match
              else "CRC changed -- Error detected")

    print(f"\n[{status}] '{filepath}'")
    print(f"  Method:        {method_name}")
    print(f"  Reference CRC: {reference_crc}")
    print(f"  Current CRC:   {current_crc}")
    print(f"  {label}")

    _save_report(filepath, method_name, reference_crc, current_crc, status)
    return status


def _save_report(filepath, method_name, reference_crc, current_crc, status):
    """Save the verification report -- Week 1's final step before End."""
    line = (
        f"[{datetime.now().isoformat(timespec='seconds')}] "
        f"File: {filepath} | Method: {method_name} | "
        f"Reference: {reference_crc} | Current: {current_crc} | "
        f"Status: {status}\n"
    )
    with open(REPORT_FILE, "a") as f:
        f.write(line)


def view_report():
    if not os.path.exists(REPORT_FILE):
        print("No verification report yet. Run a verification first.")
        return
    print("\n--- Verification Report ---")
    with open(REPORT_FILE, "r") as f:
        print(f.read())


# ============================================================
# WEEK 3 -- ERROR SIMULATION METHODS
# Each function takes the ORIGINAL file and produces a MODIFIED
# copy on disk, returning the new file's path. The original file
# is never touched, so the reference CRC stays valid throughout.
# ============================================================

def _is_text_file(filepath):
    """Check whether a file can safely be read as UTF-8 text.
    DOCX, PDF, ZIP, images etc. are binary and will fail this check."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            f.read()
        return True
    except UnicodeDecodeError:
        return False


def _read_text(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def _write_text(filepath, content):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def _byte_level_fallback(filepath, suffix, note):
    """Used when a text-based simulation method is applied to a binary
    file (DOCX, PDF, ZIP, images...). Instead of crashing, we flip one
    byte -- the closest binary equivalent of 'change one character'."""
    data = bytearray(read_file_as_bytes(filepath))
    idx = random.randrange(len(data))
    data[idx] ^= 0xFF
    out = _modified_path(filepath, suffix)
    with open(out, "wb") as f:
        f.write(data)
    return out, f"{note} (binary file detected -- changed 1 byte at offset {idx} instead)"


def sim_change_character(filepath):
    """1. Change one character in a text file."""
    if not _is_text_file(filepath):
        return _byte_level_fallback(filepath, "char_changed",
                                     "Requested: change one character")
    text = list(_read_text(filepath))
    idx = random.randrange(len(text))
    text[idx] = "X" if text[idx] != "X" else "Y"
    out = _modified_path(filepath, "char_changed")
    _write_text(out, "".join(text))
    return out, "Changed one character in the text"


def sim_modify_csv_value(filepath):
    """2. Modify one numerical value in a CSV file."""
    if not _is_text_file(filepath):
        return _byte_level_fallback(filepath, "csv_value_changed",
                                     "Requested: modify a numerical value")
    lines = _read_text(filepath).splitlines()
    for i in range(1, len(lines)):
        parts = lines[i].split(",")
        for j, p in enumerate(parts):
            if p.strip().isdigit():
                parts[j] = str(int(p.strip()) + 5)
                lines[i] = ",".join(parts)
                out = _modified_path(filepath, "csv_value_changed")
                _write_text(out, "\n".join(lines))
                return out, "Modified one numerical value in a CSV row"
    out = _modified_path(filepath, "csv_value_changed")
    _write_text(out, "\n".join(lines))
    return out, "No numeric value found to modify"


def sim_delete_record(filepath):
    """3. Delete one record (line) from the file."""
    if not _is_text_file(filepath):
        return _byte_level_fallback(filepath, "record_deleted",
                                     "Requested: delete one record")
    lines = _read_text(filepath).splitlines()
    if len(lines) > 1:
        del lines[random.randrange(1, len(lines))]
    out = _modified_path(filepath, "record_deleted")
    _write_text(out, "\n".join(lines))
    return out, "Deleted one record (line) from the file"


def sim_add_record(filepath):
    """4. Add an extra record (line) to the file."""
    if not _is_text_file(filepath):
        return _byte_level_fallback(filepath, "record_added",
                                     "Requested: add an extra record")
    text = _read_text(filepath)
    text += "\n[INJECTED] extra record not present in original"
    out = _modified_path(filepath, "record_added")
    _write_text(out, text)
    return out, "Added an extra record (line) to the file"


def sim_truncate(filepath):
    """5. Truncate a message (cut off part of the file)."""
    data = read_file_as_bytes(filepath)
    cut = max(1, int(len(data) * 0.6))
    out = _modified_path(filepath, "truncated")
    with open(out, "wb") as f:
        f.write(data[:cut])
    return out, "Truncated the file, cutting off remaining content"


def sim_change_byte_in_copy(filepath):
    """6. Change a byte in a copied file (original left untouched)."""
    data = bytearray(read_file_as_bytes(filepath))
    idx = random.randrange(len(data))
    data[idx] ^= 0xFF
    out = _modified_path(filepath, "byte_changed_copy")
    with open(out, "wb") as f:
        f.write(data)
    return out, f"Copied the file and changed one byte at offset {idx}"


def sim_random_bit_error(filepath):
    """7. Introduce a random bit error in a packet (single bit flip)."""
    data = bytearray(read_file_as_bytes(filepath))
    idx = random.randrange(len(data))
    bit = 1 << random.randrange(8)
    data[idx] ^= bit
    out = _modified_path(filepath, "bit_error")
    with open(out, "wb") as f:
        f.write(data)
    return out, f"Introduced a random single-bit error at byte offset {idx}"


def sim_rename_only(filepath):
    """8. Rename the file and check whether the content-based CRC changes.
    Content is untouched -- this should still verify as VALID, proving
    the CRC depends on content, not filename."""
    data = read_file_as_bytes(filepath)
    out = _modified_path(filepath, "renamed_only")
    with open(out, "wb") as f:
        f.write(data)
    return out, "Renamed the file only -- content bytes are identical"


def sim_exact_copy(filepath):
    """9. Copy the file exactly (Week 1: 'Transfer, copy, or modify the
    input'). An exact copy has identical bytes to the original, so this
    should also verify as VALID -- proving a clean transfer/copy is
    correctly recognised as unchanged, not flagged as an error."""
    data = read_file_as_bytes(filepath)
    out = _modified_path(filepath, "exact_copy")
    with open(out, "wb") as f:
        f.write(data)
    return out, "Created an exact copy -- every byte is identical to the original"


def _modified_path(original_path, suffix):
    base, ext = os.path.splitext(original_path)
    return f"{base}__{suffix}{ext}"


SIMULATION_METHODS = {
    "1": ("Change one character in a text file", sim_change_character),
    "2": ("Modify one numerical value in a CSV file", sim_modify_csv_value),
    "3": ("Delete one record", sim_delete_record),
    "4": ("Add an extra record", sim_add_record),
    "5": ("Truncate a message", sim_truncate),
    "6": ("Change a byte in a copied file", sim_change_byte_in_copy),
    "7": ("Introduce a random bit error in a packet", sim_random_bit_error),
    "8": ("Rename the file (content-based CRC check)", sim_rename_only),
    "9": ("Copy the file exactly (transfer/copy test)", sim_exact_copy),
}