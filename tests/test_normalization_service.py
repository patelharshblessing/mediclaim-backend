# tests/test_comprehensive_normalization.py

import os
import sys

# Add the root project directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from app.normalization_service import NormalizationService
except FileNotFoundError:
    print(
        "\nERROR: Index files not found. Run 'scripts/build_vector_db.py' before testing."
    )
    sys.exit(1)

# --- Test Data ---
# A comprehensive list of test cases covering many scenarios.
# Format: (input_description, expected_id, expected_category)
# Use None for expected_id if no match is expected.
NORMALIZATION_TEST_CASES = [
    # == Category: Room Charges ==
    ("Intensive Care Unit Charges per day", "RC06", "Room Charges"),
    ("ICU charges", "RC06", "Room Charges"),
    ("private room accomodation", "RC03", "Room Charges"),
    # == Category: Professional Fees ==
    ("Follow-up Doctor Consultation Fee", "PF02", "Professional Fees"),
    ("fee for consulting with a doctor", "PF01", "Professional Fees"),
    ("Anesthetist's Fee", "PF07", "Professional Fees"),
    ("Anestesia charges", "PF07", "Professional Fees"),  # Typo
    # == Category: Procedure Charges ==
    ("Operation Theatre Charges", "PROC01", "Procedure Charges"),
    ("OT charges", "PROC01", "Procedure Charges"),  # Abbreviation
    ("Minor OT fee", "PROC01", "Procedure Charges"),
    # == Category: Diagnostics ==
    ("Complete Blood Count (CBC) Test", "DIAG01", "Diagnostics"),
    ("blood test - cbc", "DIAG01", "Diagnostics"),
    ("USG of abdomen", "IMG03", "Diagnostics"),  # Abbreviation
    ("XRay of Chest", "IMG01", "Diagnostics"),  # Typo/Spacing
    # == Category: Pharmacy ==
    ("paracetamol tablet", "PHARM01", "Pharmacy"),
    ("IV fluid - Normal Saline", "PHARM07", "Pharmacy"),
    # == Category: Implants ==
    ("Drug-Eluting Coronary Stent", "IMP01", "Implants"),
    ("Knee joint prosthetic", "IMP04", "Implants"),  # Rephrasing
    # == Category: Non-Payable Consumables ==
    ("Disposable Surgical Gloves", "NP01", "Non-Payable Consumable"),
    ("box of surgical face masks", "NP02", "Non-Payable Consumable"),  # With noise
    ("disposable syrenge", "NP04", "Non-Payable Consumable"),  # Typo
    ("Cotton roll", "NP07", "Non-Payable Consumable"),
    ("Urine bag", "NP10", "Non-Payable Consumable"),
    # == Category: Administrative & Other Charges ==
    ("Hospital Registration Fee", "ADM01", "Administrative Charges"),
    ("Ambulance services", "OTH01", "Other Charges"),
    # == Category: No Match Expected ==
    ("Food for visitor", None, None),
    ("Photocopying of records", None, None),
    ("Television remote charges", None, None),
]


def run_tests():
    """
    Initializes the service and runs all test cases.
    """
    # Colors for printing results
    GREEN = "\033[92m"
    RED = "\033[91m"
    RESET = "\033[0m"

    print("--- Initializing NormalizationService for testing ---")
    try:
        service = NormalizationService()
    except Exception as e:
        print(f"{RED}Failed to initialize service: {e}{RESET}")
        return

    passed_count = 0
    failed_count = 0

    print("\n--- Running Normalization Tests ---")
    for description, expected_id, expected_category in NORMALIZATION_TEST_CASES:
        result = service.normalize_description(description)
        test_passed = False

        if expected_id is None:
            if result is None:
                test_passed = True
            else:
                reason = f"Expected no match, but got '{result['id']}'"
        else:
            if result is None:
                reason = "Expected a match, but got None"
            elif result["id"] != expected_id:
                reason = f"Expected ID '{expected_id}', but got '{result['id']}'"
            elif result["category"] != expected_category:
                reason = f"Expected category '{expected_category}', but got '{result['category']}'"
            else:
                test_passed = True

        if test_passed:
            print(f"{GREEN}[PASS]{RESET} '{description}'")
            passed_count += 1
        else:
            print(f"{RED}[FAIL]{RESET} '{description}' -> {reason}")
            failed_count += 1

    print("\n--- Test Summary ---")
    print(f"{GREEN}Passed: {passed_count}{RESET}")
    print(f"{RED}Failed: {failed_count}{RESET}")
    print("--------------------")


# --- Main execution block ---
if __name__ == "__main__":
    run_tests()
