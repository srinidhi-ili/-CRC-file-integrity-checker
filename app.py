"""
app.py
Flask dashboard for the CRC-32 File Integrity Checker.
Wraps crc_core.py (Week 1 core logic + Week 3 error simulation methods)
in a web UI so it can be demoed from a browser.

Run:  python app.py
Then open: http://localhost:5000
"""

import os
import json
from flask import Flask, render_template, request, redirect, url_for

import crc_core as core

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_stored_files():
    """Every file that currently has a reference CRC stored."""
    store = core._load_store()
    return sorted(store.items(), key=lambda kv: kv[1].get("stored_at", ""), reverse=True)


def get_history():
    """Parse verification_report.txt into rows for the dashboard table."""
    if not os.path.exists(core.REPORT_FILE):
        return []
    rows = []
    with open(core.REPORT_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ts_part, rest = line.split("] ", 1)
                row = {"time": ts_part.strip("[")}
                for field in rest.split(" | "):
                    key, value = field.split(": ", 1)
                    row[key.strip()] = value.strip()
                rows.append(row)
            except ValueError:
                continue
    rows.reverse()
    return rows


@app.route("/")
def dashboard():
    history = get_history()
    total = len(history)
    valid = sum(1 for h in history if h.get("Status") == "VALID")
    corrupted = total - valid

    return render_template(
        "index.html",
        history=history,
        total=total,
        valid=valid,
        corrupted=corrupted,
        stored_files=get_stored_files(),
        methods=core.SIMULATION_METHODS,
    )


@app.route("/store", methods=["POST"])
def store():
    file = request.files.get("file")
    if file and file.filename:
        path = os.path.join(UPLOAD_DIR, file.filename)
        file.save(path)
        core.store_reference_crc(path)
    return redirect(url_for("dashboard"))


@app.route("/verify", methods=["POST"])
def verify():
    filepath = request.form.get("filepath")
    if filepath:
        core.verify_file(filepath)
    return redirect(url_for("dashboard"))


@app.route("/simulate", methods=["POST"])
def simulate():
    filepath = request.form.get("filepath")
    method_key = request.form.get("method")
    method = core.SIMULATION_METHODS.get(method_key)

    if filepath and method:
        label, func = method
        try:
            modified_path, description = func(filepath)
        except Exception as e:
            # Never let a bad file (corrupted, empty, permission error)
            # crash the whole dashboard -- just skip this simulation.
            print(f"[ERROR] Simulation failed: {e}")
            return redirect(url_for("dashboard"))

        # Carry the original file's reference CRC over to the new
        # modified copy so verify_file() can look it up.
        store = core._load_store()
        original_key = os.path.abspath(filepath)
        if original_key in store:
            store[os.path.abspath(modified_path)] = store[original_key]
            with open(core.REFERENCE_STORE, "w") as f:
                json.dump(store, f, indent=2)
            core.verify_file(modified_path, method_name=label)

    return redirect(url_for("dashboard"))


@app.route("/clear", methods=["POST"])
def clear_all():
    """Wipe all stored reference CRCs, history, and uploaded files --
    a clean slate for a new demo."""
    if os.path.exists(core.REFERENCE_STORE):
        os.remove(core.REFERENCE_STORE)
    if os.path.exists(core.REPORT_FILE):
        os.remove(core.REPORT_FILE)
    for fname in os.listdir(UPLOAD_DIR):
        fpath = os.path.join(UPLOAD_DIR, fname)
        if os.path.isfile(fpath):
            os.remove(fpath)
    return redirect(url_for("dashboard"))


# ============================================================
# 1-CLICK LAB DEMONSTRATION CONTROLS
# Runs the full Week 1 + Week 3 workflow end-to-end in 4 clicks,
# so both flowcharts can be demoed live without manual file editing.
# ============================================================

SAMPLE_FILES = {
    "sample_report.txt": (
        "Lab Report 2026\nStudent: Srinidhi\nSubject: CRC-32 file integrity\n"
        "Status: original unmodified content\nEnd of file."
    ),
    "sample_attendance.csv": (
        "id,name,marks\n1,Aditi,88\n2,Rohan,76\n3,Kavya,91\n4,Meera,69"
    ),
}


@app.route("/demo/load", methods=["POST"])
def demo_load():
    """Step 1: create fresh sample files to demo with."""
    for name, content in SAMPLE_FILES.items():
        path = os.path.join(UPLOAD_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    return redirect(url_for("dashboard"))


@app.route("/demo/store_all", methods=["POST"])
def demo_store_all():
    """Step 2: store a reference CRC for every uploaded file that
    doesn't have one yet (covers Week 1: select input -> read bytes
    -> calculate CRC-32 -> store reference)."""
    store = core._load_store()
    for fname in os.listdir(UPLOAD_DIR):
        fpath = os.path.join(UPLOAD_DIR, fname)
        if os.path.isfile(fpath) and os.path.abspath(fpath) not in store:
            core.store_reference_crc(fpath)
    return redirect(url_for("dashboard"))


@app.route("/demo/corrupt_all", methods=["POST"])
def demo_corrupt_all():
    """Step 3: run every Week 3 error simulation method once, across
    the currently stored original files, and verify each result."""
    store = core._load_store()
    # Only touch "original" files, not previously-simulated copies
    originals = [p for p in store.keys() if "__" not in os.path.basename(p)]

    method_items = list(core.SIMULATION_METHODS.items())
    for i, original_path in enumerate(originals):
        if not os.path.exists(original_path):
            continue
        key, (label, func) = method_items[i % len(method_items)]
        try:
            modified_path, _ = func(original_path)
        except Exception as e:
            print(f"[ERROR] Demo simulation failed for {original_path}: {e}")
            continue
        store[os.path.abspath(modified_path)] = store[original_path]
        with open(core.REFERENCE_STORE, "w") as f:
            json.dump(store, f, indent=2)
        core.verify_file(modified_path, method_name=label)

    return redirect(url_for("dashboard"))


@app.route("/demo/verify_all", methods=["POST"])
def demo_verify_all():
    """Step 4: recalculate and verify every file that currently has a
    reference CRC stored (Week 1's compare + display VALID/CORRUPTED)."""
    store = core._load_store()
    for path in list(store.keys()):
        if os.path.exists(path):
            core.verify_file(path)
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)