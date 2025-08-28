# app/rules_engine.py
# app/rules_engine.py
import sys 
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# --------------------------------------------

import asyncio
from datetime import date
from app.pydantic_schemas import ExtractedData, AdjudicatedClaim, AdjudicatedLineItem, InsuranceDetails, LineItem
from app.data.master_data import POLICY_RULEBOOK
from app.rules_utils import (
    identify_non_payable_items, 
    get_rule_match_with_llm, 
    apply_policy_rule_with_llm_tools
)
from app.normalization_service import NormalizationService


async def adjudicate_claim(
    extracted_data: ExtractedData,
    insurance_details: InsuranceDetails
) -> AdjudicatedClaim:
    """
    The main orchestrator for the adjudication pipeline. It applies a series
    of rules to determine the final payable amount.

    Args:
        extracted_data: The user-verified data from the bill.
        insurance_details: The policy details for the claim.

    Returns:
        The final, fully adjudicated claim object.
    """
    # --- Step 0: Create a copy of input ExtractedData to AdjudicatedClaim ---
    
    # Create AdjudicatedLineItem objects from the simple LineItem objects.
    # We initialize them as "Allowed" with the full amount.
    policy=POLICY_RULEBOOK[insurance_details.policy_number]
    # print(policy)
    initial_adjudicated_items = [
        AdjudicatedLineItem(
            **item.model_dump(), # Copies description, quantity, etc.
            status="Allowed",
            allowed_amount=item.total_amount,
            disallowed_amount=0.0,
            reason=None
        )
        for item in extracted_data.line_items
    ]
    
    # Create the main AdjudicatedClaim object that we will work with.
    adjudicated_claim = AdjudicatedClaim(
        # Copy all header fields from the input data
        hospital_name=extracted_data.hospital_name,
        patient_name=extracted_data.patient_name,
        bill_no=extracted_data.bill_no,
        bill_date=extracted_data.bill_date,
        admission_date=extracted_data.admission_date,
        discharge_date=extracted_data.discharge_date,
        
        # Use the newly created list of adjudicated items
        adjudicated_line_items=initial_adjudicated_items,
        
        # Initialize total amounts
        total_claimed_amount=extracted_data.net_payable_amount,
        total_allowed_amount=extracted_data.net_payable_amount, # Starts as the full amount
        adjustments_log=[]
    )

    # In the next steps, we will modify this 'adjudicated_claim' object.
    
    # --- Step 1: Find and update IRDAI non-payable items ---
    
    # First, get the list of items identified as non-payable.
    normalizationservice=NormalizationService()
    non_payable_list = identify_non_payable_items(
        line_items=adjudicated_claim.adjudicated_line_items,
        service=normalizationservice
    )
    # Create a set of descriptions for fast lookup.
    non_payable_descriptions = [item.description for item in non_payable_list]
    print(non_payable_descriptions)
    # Now, loop through the main list and update the status for matching items.
    total_disallowed_IRDAI=0.0
    for item in adjudicated_claim.adjudicated_line_items:
        if item.description in non_payable_descriptions:
            total_disallowed_IRDAI=total_disallowed_IRDAI+item.allowed_amount
            item.status = "Disallowed"
            item.allowed_amount = 0.0
            item.disallowed_amount = item.total_amount
            item.reason = "Non-payable item as per IRDAI guidelines."
    items=",".join(non_payable_descriptions)
    if total_disallowed_IRDAI>0.0:
        adjudicated_claim.adjustments_log.append(f"The items {items}  not allowed because they are categorised as Non-Payable by IRDAI constituting to: ₹{total_disallowed_IRDAI:,.2f}")
    # In the next steps, we will add more rules to modify this object further.
    

    # --- Step 2: Find Matching Sub-Limit Rules in Parallel ---
    print("--- Starting Step 2: Finding matching policy rules in parallel... ---")
    # print(POLICY_RULEBOOK)
    sub_limits = policy.get("sub_limits", {})
    
    # Create a list of tasks to run concurrently
    match_tasks = []
    items_to_process = []
    for item in adjudicated_claim.adjudicated_line_items:
        # Only check items that are still allowed
        if item.status != "Disallowed":
            items_to_process.append(item)
            match_tasks.append(get_rule_match_with_llm(item.description, sub_limits))
    
    # Run all the LLM calls for rule matching at the same time
    matched_rule_names = await asyncio.gather(*match_tasks)
    
    # --- Step 3: Apply Matched Rules ---
    print("\n--- Starting Step 3: Applying matched rules... ---")
    final_adjudicated_items = []
    items_to_update = []
    update_tasks = []
    sum_insured=policy['sum_insured']
    for i, item in enumerate(items_to_process):
        rule_name = matched_rule_names[i]
        if rule_name and rule_name in sub_limits:
            print(f"Rule '{rule_name}' applies to item '{item.description}'. Preparing to apply.")
            policy_rule_to_apply = sub_limits[rule_name]
            # Create a task to apply the rule (can also be run in parallel)
            update_tasks.append(
                apply_policy_rule_with_llm_tools(item, policy_rule_to_apply, sum_insured)
            )
            items_to_update.append(item)
        else:
            # If no rule applies, keep the item as is
            final_adjudicated_items.append(item)

    # Run the rule application calls
    if update_tasks:
        updated_items = await asyncio.gather(*update_tasks)
        final_adjudicated_items.extend(updated_items)
    
    # Add back the items that were already disallowed from Step 1
    disallowed_items = [item for item in adjudicated_claim.adjudicated_line_items if item.status == "Disallowed"]
    final_adjudicated_items.extend(disallowed_items)
    
    adjudicated_claim.adjudicated_line_items = final_adjudicated_items
    
    total_disallowed_policy=0.0
    for items in adjudicated_claim.adjudicated_line_items : 
        if items.reason!="Non-payable item as per IRDAI guidelines." :
            total_disallowed_policy+=items.disallowed_amount
    if total_disallowed_policy > 0.0:
        # Log the total disallowed amount due to policy rules
        adjudicated_claim.adjustments_log.append(
            f"The amount deducted due to  insurance policy rules is: ₹{total_disallowed_policy:,.2f}."
        )
    print(f"Total disallowed due to policy rules: ₹{total_disallowed_policy:,.2f}")
    # --- Step 4: Final Calculations & Claim-Level Rules ---
    print("\n--- Starting Step 4: Final Calculations & Claim-Level Rules ---")

    # 4a. Recalculate the true totals after all item-level rules
    final_total_allowed = sum(item.allowed_amount for item in adjudicated_claim.adjudicated_line_items)
    
    adjudicated_claim.total_allowed_amount = final_total_allowed
    
    # 4b. Apply the co-payment rule
    co_payment_percentage = policy.get("co_payment_percentage", 0)
    co_payment_amount = 0.0
    
    if co_payment_percentage > 0:
        co_payment_amount = (final_total_allowed * co_payment_percentage) / 100
        adjudicated_claim.adjustments_log.append(
            f"Applied {co_payment_percentage}% co-payment on allowed amount: ₹{co_payment_amount:,.2f}"
        )

    amount_after_copay = final_total_allowed - co_payment_amount
    
    # --- NEW: Rule 4 - Capping to Sum Insured ---
    final_payable = min(amount_after_copay, sum_insured)

    if final_payable < amount_after_copay:
        # This condition is true only if the sum insured limit was hit
        adjudicated_claim.adjustments_log.append(
            f"Final amount capped at the policy's Sum Insured of ₹{sum_insured:,.2f}."
        )
    
    adjudicated_claim.total_allowed_amount = final_payable
    
    # --- Step 5: Return the Final Object ---
    print("\n--- ✅ Adjudication Complete ---")
    return adjudicated_claim


# --- Main execution block to test the function ---
if __name__ == "__main__":
    # A comprehensive sample data object to test multiple sub-limit rules.
    # Represents a 5-day hospital stay for a surgical procedure.
    comprehensive_sample_data = ExtractedData(
        hospital_name="Apollo Spectra Hospital, Kanpur",
        patient_name="A. K. Srivastava",
        bill_no="ASHK-2025-08-123",
        bill_date=date(2025, 8, 21),
        admission_date=date(2025, 8, 17),
        discharge_date=date(2025, 8, 21), # 5 days total
        line_items=[
            # 1. To test "Room Charges" (will exceed the 7,500/day cap)
            LineItem(description="Private A/C Room Rent", quantity=5, unit_price=8000, total_amount=40000.0),
            
            # 2. To test "ICU Charges" (under the 15,000/day cap)
            LineItem(description="Intensive Care Unit (1 day)", quantity=1, unit_price=12000, total_amount=12000.0),
            
            # 3. To test "Doctor Consultation" (will exceed the 2,000/day cap)
            LineItem(description="Daily Doctor Visits", quantity=5, unit_price=2500, total_amount=12500.0),
            
            # 4. To test "Surgeon Fees"
            LineItem(description="Lead Surgeon Fee for Appendectomy", quantity=1, unit_price=60000, total_amount=60000.0),
            
            # 5. To test "Anesthetist Fees"
            LineItem(description="Anesthetist Charges", quantity=1, unit_price=20000, total_amount=20000.0),
            
            # 6. To test "Nursing Charges" (under the 1,000/day cap)
            LineItem(description="Special Nursing Care", quantity=5, unit_price=800, total_amount=4000.0),
            
            # 7. & 8. To test Pharmacy and Diagnostics (will exceed percentage caps)
            LineItem(description="Pharmacy and Medicines", quantity=1, unit_price=60000, total_amount=60000.0),
            LineItem(description="Diagnostic Tests (CT, Blood)", quantity=1, unit_price=80000, total_amount=80000.0),
            
            # 9. To test "Ambulance Charges" (will exceed the 3,000 fixed cap)
            LineItem(description="Ambulance Service", quantity=1, unit_price=4000, total_amount=4000.0),

            # 14. To test "Maternity" (hypothetical, to show a package item)
            # LineItem(description="Normal Delivery Package", quantity=1, unit_price=45000, total_amount=45000.0),

            # 15. To test "Cataract Surgery" (hypothetical, will exceed 40k cap)
            # LineItem(description="Cataract Surgery - Left Eye", quantity=1, unit_price=55000, total_amount=55000.0),
            
            # A non-payable item to test the first filter
            LineItem(description="Hospital Admission Kit", quantity=1, unit_price=1500, total_amount=1500.0)
        ],
        net_payable_amount=294000.0
    )

    # 2. Create sample InsuranceDetails
    sample_policy = InsuranceDetails(
        policy_number="MVP1",
        insurance_provider="MediSure"
    )
    async def run_def() :
        # 3. Call the adjudicate_claim function
        print("--- Calling adjudicate_claim ---")
        final_claim =await adjudicate_claim(
            extracted_data=comprehensive_sample_data,
            insurance_details=sample_policy
        )

        print(final_claim.model_dump_json(indent=2))


    # 4. Print the result
    # We use .model_dump_json for a clean, indented print of the Pydantic object
    print("--- Output of Step 0 ---")
    asyncio.run(run_def())
