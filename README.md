# CRC-32 File Integrity Checker

A tool that tells you whether a file is still **exactly the same** as the original, using CRC-32 checksums.



---

## The idea

A student saves files on a lab computer. After copying or editing, a file can change without anyone noticing.

So we give every file a **fingerprint** (its CRC-32 checksum):

1. Read the file as raw bytes
2. Calculate its CRC-32 fingerprint
3. Store it as the **reference**
4. Later, calculate the fingerprint again and compare
5. Same fingerprint = **VALID**. Different = **CORRUPTED**
6. Every check is saved in a verification report

Change even one byte and the fingerprint changes completely.

---

## How we prove it works

We deliberately break files in 9 ways and check the tool reacts correctly:

| Result | Methods |

| **CORRUPTED** (content really changed) | change a character, edit a CSV value, delete a record, add a record, truncate, change a byte, flip a random bit |
| **VALID** (content untouched) | rename the file, make an exact copy |

The two VALID cases show the checker looks at file **content**, not the filename.

---

## Project structure

```
crc.pro/
├── crc_core.py        # all CRC logic + the 9 error simulations
├── main.py            # command-line version
├── app.py             # Flask web dashboard (backend)
└── templates/
    └── index.html     # dashboard page (frontend)
```

`crc_core.py` is the single brain. Both `main.py` and `app.py` call it, so there is only one implementation to test.

---

## How to run

```
python -m pip install flask
python app.py
```



---

## Built with

Python 3, `zlib` (CRC-32), Flask, Jinja2, HTML/CSS, JSON

## Limitation

CRC-32 catches **accidental** corruption. It is not secure against deliberate tampering. For that, use SHA-256.
