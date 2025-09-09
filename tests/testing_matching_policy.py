# scripts/compare_matching_methods.py
import asyncio
import os
import sys

# Add the root project directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.rules_utils import get_rule_match_with_llm
from app.normalization_service import NormalizationService
from app.data.master_data import POLICY_RULEBOOK

# scripts/compare_matching_methods.py

# A list of test cases with the raw description and the expected policy rule name.
# scripts/large_test_cases.py

# An extensive list of 50 test cases to benchmark the accuracy of the LLM rule matcher.
# Format: (input_description, expected_policy_rule_name)

MATCHING_TEST_CASES = [
    # --- Simple, Direct Matches ---
    ("Room Rent for Semi-Private Ward", "Room Charges"),
    ("Intensive Care Unit Charges", "ICU Charges"),
    ("Ambulance Service Fee", "Ambulance"),
    ("Doctor Consultation Fee", "Doctor Consultation"),
    ("Surgeon Fees for Surgery", "Surgeon Fees"),
    ("Anesthetist Charges", "Anesthetist Fees"),
    ("Nursing Charges per Day", "Nursing Charges"),
    ("Pharmacy and Medicines", "Pharmacy"),
    ("Diagnostic Tests (X-ray, MRI)", "Diagnostics"),
    ("Pre-Hospitalization Expenses", "Pre-Hospitalization"),
    ("Post-Hospitalization Expenses", "Post-Hospitalization"),
    ("Daycare Procedure Charges", "Daycare Procedures"),
    ("Room Rent for Private Ward", "Room Charges"),
    ("ICU Bed Charges", "ICU Charges"),
    ("Ambulance Charges for Emergency", "Ambulance"),
    ("Doctor Visit Fee", "Doctor Consultation"),
    ("Lead Surgeon Fee", "Surgeon Fees"),
    ("Anesthesia Fee", "Anesthetist Fees"),
    ("Special Nursing Charges", "Nursing Charges"),
    ("Medicines and Consumables", "Pharmacy"),
    ("Lab Tests and Imaging", "Diagnostics"),
    ("Pre-Hospitalization Medical Bills", "Pre-Hospitalization"),
    ("Post-Hospitalization Follow-Up", "Post-Hospitalization"),
    ("Cataract Surgery Charges", "Daycare Procedures"),
    ("Room Rent for General Ward", "Room Charges"),
    ("ICU Ventilator Charges", "ICU Charges"),
    ("Emergency Ambulance Service", "Ambulance"),
    ("Consultation with Specialist", "Doctor Consultation"),
    ("Surgical Procedure Fee", "Surgeon Fees"),
    ("Anesthetist Fee for Surgery", "Anesthetist Fees"),
    ("Nursing Care Charges", "Nursing Charges"),
    ("Pharmacy Bills", "Pharmacy"),
    ("Diagnostic Imaging (CT Scan)", "Diagnostics"),
    ("Pre-Hospitalization Checkup", "Pre-Hospitalization"),
    ("Post-Hospitalization Therapy", "Post-Hospitalization"),
    ("Daycare Chemotherapy", "Daycare Procedures"),
    ("Room Rent for Deluxe Room", "Room Charges"),
    ("ICU Monitoring Charges", "ICU Charges"),
    ("Ambulance for Hospital Transfer", "Ambulance"),
    ("General Physician Consultation", "Doctor Consultation"),
    ("Surgical Team Fee", "Surgeon Fees"),
    ("Anesthesia Administration Fee", "Anesthetist Fees"),
    ("Nursing Assistance Charges", "Nursing Charges"),
    ("Pharmacy and Drug Costs", "Pharmacy"),
    ("Lab Tests (Blood, Urine)", "Diagnostics"),
    ("Pre-Hospitalization Diagnostics", "Pre-Hospitalization"),
    ("Post-Hospitalization Medicines", "Post-Hospitalization"),
    ("Daycare Dialysis Procedure", "Daycare Procedures"),
    ("Room Rent for Shared Room", "Room Charges"),
    ("ICU Nursing Charges", "ICU Charges")
]


async def run_comparison():
    """
    Runs a side-by-side comparison of the NormalizationService and the LLM-based
    rule matching methods and prints an accuracy report.
    """
    print("--- Starting Rule Matching Method Comparison ---")
    
    # Initialize the local service
    normalization_service = NormalizationService()
    
    # Prepare data for the test
    sub_limits = POLICY_RULEBOOK["MVP1"]["sub_limits"]
    descriptions = [case[0] for case in MATCHING_TEST_CASES]
    
    # --- Run the LLM-based method for all items in parallel ---
    print("\nStep 1: Running LLM-based matching (this may take a moment)...")
    llm_tasks = [get_rule_match_with_llm(desc, sub_limits) for desc in descriptions]
    llm_results = await asyncio.gather(*llm_tasks)
    print("LLM matching complete.")
    
    # --- Run the NormalizationService method for all items ---
    print("\nStep 2: Running local NormalizationService matching (this will be instant)...")
    norm_results = []
    for desc in descriptions:
        normalized = normalization_service.normalize_description(desc)
        # The category is the matched rule name
        norm_results.append(normalized['category'] if normalized else None)
    print("NormalizationService matching complete.")
    

    # --- Step 3: Compare results and generate report ---
    norm_correct = 0
    llm_correct = 0
    
    # (Colors for printing)
    GREEN = "\033[92m"
    RED = "\033[91m"
    RESET = "\033[0m"

    print("\n" + "="*80)
    print("                         Accuracy Comparison Report")
    # ...

    for i, case in enumerate(MATCHING_TEST_CASES):
        description, expected = case
        norm_prediction = norm_results[i]
        llm_prediction = llm_results[i]

        # --- FIX: Sanitize the LLM's output before comparing ---
        # Convert both to string, remove extra spaces, and make them lowercase
        expected_clean = str(expected or "").strip().lower()
        norm_clean = str(norm_prediction or "").strip().lower()
        llm_clean = str(llm_prediction or "").strip().lower()
        
        # Check NormalizationService accuracy
        if norm_clean == expected_clean:
            norm_correct += 1
            norm_status = f"{GREEN}PASS{RESET}"
        else:
            norm_status = f"{RED}FAIL{RESET}"

        # Check LLM Matcher accuracy
        if llm_clean == expected_clean:
            llm_correct += 1
            llm_status = f"{GREEN}PASS{RESET}"
        else:
            llm_status = f"{RED}FAIL{RESET}"
            
        print(f"{description:<40} | {str(expected):<20} | {str(norm_prediction):<20} ({norm_status}) | {str(llm_prediction):<20} ({llm_status})")


    # --- Final Score ---
    norm_accuracy = (norm_correct / len(MATCHING_TEST_CASES)) * 100
    llm_accuracy = (llm_correct / len(MATCHING_TEST_CASES)) * 100

    print("="*80)
    print("                            Final Scores")
    print("="*80)
    print(f"NormalizationService Accuracy: {norm_accuracy:.2f}% ({norm_correct}/{len(MATCHING_TEST_CASES)} correct)")
    print(f"LLM Matcher Accuracy:          {llm_accuracy:.2f}% ({llm_correct}/{len(MATCHING_TEST_CASES)} correct)")
    print("="*80)

    if norm_accuracy > llm_accuracy:
        print(f"\n🏆 {GREEN}Winner: NormalizationService is more accurate and significantly faster/cheaper.{RESET}")
    elif llm_accuracy > norm_accuracy:
        print(f"\n🏆 {GREEN}Winner: LLM Matcher is more accurate.{RESET}")
    else:
        print("\nIt's a tie! But NormalizationService is faster and cheaper.")

if __name__ == "__main__":
    asyncio.run(run_comparison())