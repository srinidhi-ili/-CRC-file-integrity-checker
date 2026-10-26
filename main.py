"""
main.py
CRC-32 File Integrity Checker -- CLI

Product 1, Group I:
A student stores TXT, CSV, PDF, and image files on a lab computer.
During copying, storage, or accidental editing, file contents may
change without being immediately visible. This tool verifies whether
a current file is identical to the original.

Run:  python main.py
"""

import os
import crc_core as core


def menu():
    print("\n===== CRC-32 File Integrity Checker =====")
    print("1. Store reference CRC for a file (run this on the ORIGINAL file)")
    print("2. Verify a file directly (no simulated error)")
    print("3. Apply an error simulation method, then verify the result")
    print("4. View verification report")
    print("5. Exit")
    return input("Choose an option: ").strip()


def choose_file():
    path = input("Enter the file path: ").strip()
    if not os.path.exists(path):
        print("[ERROR] File not found.")
        return None
    return path


def choose_simulation_method():
    print("\nError simulation methods:")
    for key, (label, _) in core.SIMULATION_METHODS.items():
        print(f"  {key}. {label}")
    choice = input("Choose a method (1-8): ").strip()
    return core.SIMULATION_METHODS.get(choice)


def main():
    while True:
        choice = menu()

        if choice == "1":
            path = choose_file()
            if path:
                core.store_reference_crc(path)

        elif choice == "2":
            path = choose_file()
            if path:
                core.verify_file(path)

        elif choice == "3":
            path = choose_file()
            if not path:
                continue
            method = choose_simulation_method()
            if not method:
                print("[ERROR] Invalid method choice.")
                continue
            label, func = method
            modified_path, description = func(path)
            print(f"[SIMULATED] {description}")
            print(f"[SIMULATED] Modified file saved as: {modified_path}")
            # Verify the MODIFIED file against the ORIGINAL file's reference CRC.
            # We do this by copying the reference entry so verify_file can find it.
            store = core._load_store()
            original_key = os.path.abspath(path)
            if original_key not in store:
                print("[ERROR] Store a reference CRC for the original file first (option 1).")
                continue
            store[os.path.abspath(modified_path)] = store[original_key]
            with open(core.REFERENCE_STORE, "w") as f:
                import json
                json.dump(store, f, indent=2)
            core.verify_file(modified_path, method_name=label)

        elif choice == "4":
            core.view_report()

        elif choice == "5":
            print("Goodbye.")
            break

        else:
            print("[ERROR] Invalid choice.")


if __name__ == "__main__":
    main()