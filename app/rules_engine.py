# # app/rules_engine.py
# # app/rules_engine.py
# import os
# import sys

# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# # --------------------------------------------

# import asyncio
# import time
# from datetime import date
# from typing import Tuple

# from app.data.master_data import POLICY_RULEBOOK
# from app.normalization_service import NormalizationService
# from app.pydantic_schemas import (
#     AdjudicatedClaim,
#     AdjudicatedLineItem,
#     ExtractedData,
#     InsuranceDetails,
#     LineItem,
# )
# from app.rules_utils import (
#     apply_policy_rule_with_llm_tools,
#     get_rule_match_with_llm,
#     identify_non_payable_items,
#     run_final_sanity_check,
# )


# async def adjudicate_claim(
#     extracted_data: ExtractedData, insurance_details: InsuranceDetails
# ) -> Tuple[AdjudicatedClaim, dict]:
#     """
#     The main orchestrator for the adjudication pipeline. It applies a series
#     of rules to determine the final payable amount.

#     Args:
#         extracted_data: The user-verified data from the bill.
#         insurance_details: The policy details for the claim.

#     Returns:
#         The final, fully adjudicated claim object.
#     """
#     # --- Step 0: Create a copy of input ExtractedData to AdjudicatedClaim ---

#     # Create AdjudicatedLineItem objects from the simple LineItem objects.
#     # We initialize them as "Allowed" with the full amount.
#     policy = POLICY_RULEBOOK[insurance_details.policy_number]
#     # print(policy)
#     initial_adjudicated_items = [
#         AdjudicatedLineItem(
#             **item.model_dump(),  # Copies description, quantity, etc.
#             status="Allowed",
#             allowed_amount=item.total_amount,
#             disallowed_amount=0.0,
#             reason=None,
#         )
#         for item in extracted_data.line_items
#     ]

#     # Create the main AdjudicatedClaim object that we will work with.
#     adjudicated_claim = AdjudicatedClaim(
#         # Copy all header fields from the input data
#         hospital_name=extracted_data.hospital_name,
#         patient_name=extracted_data.patient_name,
#         bill_no=extracted_data.bill_no,
#         bill_date=extracted_data.bill_date,
#         admission_date=extracted_data.admission_date,
#         discharge_date=extracted_data.discharge_date,
#         # Use the newly created list of adjudicated items
#         adjudicated_line_items=initial_adjudicated_items,
#         # Initialize total amounts
#         total_claimed_amount=extracted_data.net_payable_amount,
#         total_allowed_amount=extracted_data.net_payable_amount,  # Starts as the full amount
#         adjustments_log=[],
#     )

#     # In the next steps, we will modify this 'adjudicated_claim' object.

#     # --- Step 1: Find and update IRDAI non-payable items ---

#     normalizationservice = NormalizationService()
#     non_payable_list = identify_non_payable_items(
#         line_items=adjudicated_claim.adjudicated_line_items,
#         service=normalizationservice,
#     )
#     # Create a set of descriptions for fast lookup.
#     non_payable_descriptions = [item.description for item in non_payable_list]
#     print(non_payable_descriptions)
#     # Now, loop through the main list and update the status for matching items.
#     total_disallowed_IRDAI = 0.0
#     for item in adjudicated_claim.adjudicated_line_items:
#         if item.description in non_payable_descriptions:
#             total_disallowed_IRDAI = total_disallowed_IRDAI + item.allowed_amount
#             # item.status = "Disallowed"
#             item.allowed_amount = 0.0
#             item.disallowed_amount = item.total_amount
#             item.reason = "Non-payable item as per IRDAI guidelines."
#     items = ",".join(non_payable_descriptions)
#     if total_disallowed_IRDAI > 0.0:
#         adjudicated_claim.adjustments_log.append(
#             f"The items {items}  not allowed because they are categorised as Non-Payable by IRDAI constituting to: ₹{total_disallowed_IRDAI:,.2f}"
#         )

#     # --- Step 2: Find Matching Sub-Limit Rules in Parallel ---
#     step2_start_time = time.time()
#     print("--- Starting Step 2: Finding matching policy rules in parallel... ---")
#     # print(POLICY_RULEBOOK)
#     sub_limits = policy.get("sub_limits", {})

#     # Create a list of tasks to run concurrently
#     match_tasks = []
#     items_to_process = []
#     for item in adjudicated_claim.adjudicated_line_items:
#         # Only check items that are still allowed
#         if item.status != "Disallowed":
#             items_to_process.append(item)
#             match_tasks.append(get_rule_match_with_llm(item.description, sub_limits))

#     # Run all the LLM calls for rule matching at the same time
#     matched_rule_names = await asyncio.gather(*match_tasks)
#     # --- Step 3: Apply Matched Rules ---
#     print("\n--- Starting Step 3: Applying matched rules... ---")
#     final_adjudicated_items = []
#     items_to_update = []
#     update_tasks = []
#     sum_insured = policy["sum_insured"]
#     for i, item in enumerate(items_to_process):
#         rule_name = matched_rule_names[i]
#         if rule_name and rule_name in sub_limits:
#             print(
#                 f"Rule '{rule_name}' applies to item '{item.description}'. Preparing to apply."
#             )
#             policy_rule_to_apply = sub_limits[rule_name]
#             # Create a task to apply the rule (can also be run in parallel)
#             update_tasks.append(
#                 apply_policy_rule_with_llm_tools(
#                     item, policy_rule_to_apply, sum_insured
#                 )
#             )
#             items_to_update.append(item)
#         else:
#             # If no rule applies, keep the item as is
#             final_adjudicated_items.append(item)

#     # Run the rule application calls
#     if update_tasks:
#         updated_items = await asyncio.gather(*update_tasks)
#         final_adjudicated_items.extend(updated_items)

#     # Add back the items that were already disallowed from Step 1
#     disallowed_items = [
#         item
#         for item in adjudicated_claim.adjudicated_line_items
#         if item.status == "Disallowed"
#     ]
#     final_adjudicated_items.extend(disallowed_items)

#     adjudicated_claim.adjudicated_line_items = final_adjudicated_items

#     total_disallowed_policy = 0.0
#     for items in adjudicated_claim.adjudicated_line_items:
#         if items.reason != "Non-payable item as per IRDAI guidelines.":
#             total_disallowed_policy += items.disallowed_amount
#     if total_disallowed_policy > 0.0:
#         # Log the total disallowed amount due to policy rules
#         adjudicated_claim.adjustments_log.append(
#             f"The amount deducted due to  insurance policy rules is: ₹{total_disallowed_policy:,.2f}."
#         )
#     print(f"Total disallowed due to policy rules: ₹{total_disallowed_policy:,.2f}")
#     # --- Step 4: Final Calculations & Claim-Level Rules ---
#     # print("\n--- Starting Step 4: Final Calculations & Claim-Level Rules ---")

#     # 4a. Recalculate the true totals after all item-level rules
#     final_total_allowed = sum(
#         item.allowed_amount for item in adjudicated_claim.adjudicated_line_items
#     )

#     adjudicated_claim.total_allowed_amount = final_total_allowed

#     # 4b. Apply the co-payment rule
#     co_payment_percentage = policy.get("co_payment_percentage", 0)
#     co_payment_amount = 0.0

#     if co_payment_percentage > 0:
#         co_payment_amount = (final_total_allowed * co_payment_percentage) / 100
#         adjudicated_claim.adjustments_log.append(
#             f"Applied {co_payment_percentage}% co-payment on allowed amount: ₹{co_payment_amount:,.2f}"
#         )

#     amount_after_copay = final_total_allowed - co_payment_amount

#     # --- NEW: Rule 4 - Capping to Sum Insured ---
#     final_payable = min(amount_after_copay, sum_insured)

#     if final_payable < amount_after_copay:
#         # This condition is true only if the sum insured limit was hit
#         adjudicated_claim.adjustments_log.append(
#             f"Final amount capped at the policy's Sum Insured of ₹{sum_insured:,.2f}."
#         )

#     adjudicated_claim.total_allowed_amount = final_payable
#     # --- Step 5: Final AI Sanity Check (The AI Auditor) ---
#     print("\n--- Starting Step 5: Final AI Sanity Check ---")

#     # The 'adjudicated_claim' object is now fully calculated.
#     # We pass it to our new auditor for a final review.
#     sanity_result = await run_final_sanity_check(adjudicated_claim)

#     # Attach the auditor's report to the final claim object
#     adjudicated_claim.sanity_check_result = sanity_result

#     print("--- ✅ Adjudication and Final Audit Complete ---")
#     return adjudicated_claim


import asyncio
import os
import sys
import time
from typing import Tuple

from fastapi import HTTPException

# Add the root project directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from uuid import UUID

from app.data.master_data import POLICY_RULEBOOK
from app.normalization_service import NormalizationService
from app.pydantic_schemas import (
    AdjudicatedClaim,
    AdjudicatedLineItem,
    ExtractedData,
    InsuranceDetails,
)
from app.rules_utils import (
    apply_policy_rule_with_llm_tools,
    get_rule_match_with_llm,
    identify_non_payable_items,
    run_final_sanity_check,
)


async def adjudicate_claim(
    extracted_data: ExtractedData,
    insurance_details: InsuranceDetails,
    normalizationservice: NormalizationService,
) -> Tuple[AdjudicatedClaim, dict]:
    """
    The main orchestrator for the adjudication pipeline. It applies a series
    of rules to determine the final payable amount.

    Args:
        extracted_data: The user-verified data from the bill.
        insurance_details: The policy details for the claim.
        normalizationservice: An instance of the NormalizationService.

    Returns:
        A tuple containing the final adjudicated claim object and a dictionary
        of performance metrics.
    """
    # --- Performance Tracking Initialization ---
    total_adjudication_start_time = time.monotonic()
    perf_metrics = {
        "total_items_processed": len(extracted_data.line_items),
        "rules_applied_count": 0,
    }

    # --- Step 0: Initial Setup ---
    try:
        policy = POLICY_RULEBOOK[insurance_details.policy_number]
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Policy number '{insurance_details.policy_number}' not found.",
        )

    initial_adjudicated_items = [
        AdjudicatedLineItem(
            **item.model_dump(),
            # status="Allowed",
            allowed_amount=item.total_amount,
            disallowed_amount=0.0,
            reason=None,
        )
        for item in extracted_data.line_items
    ]

    adjudicated_claim = AdjudicatedClaim(
        # --- ADD ALL THE MISSING FIELDS HERE ---
        hospital_name=extracted_data.hospital_name,
        patient_name=extracted_data.patient_name,
        bill_no=extracted_data.bill_no,
        bill_date=extracted_data.bill_date,
        admission_date=extracted_data.admission_date,
        discharge_date=extracted_data.discharge_date,
        # --- END OF CHANGE ---
        adjudicated_line_items=initial_adjudicated_items,
        total_claimed_amount=extracted_data.net_payable_amount,
        total_allowed_amount=extracted_data.net_payable_amount,
        adjustments_log=[],
    )
    # --- Step 1: IRDAI Non-Payable Items ---
    step1_start_time = time.monotonic()
    non_payable_list = identify_non_payable_items(
        line_items=adjudicated_claim.adjudicated_line_items,
        service=normalizationservice,
    )
    non_payable_descriptions = {item.description for item in non_payable_list}

    total_disallowed_IRDAI = 0.0
    for item in adjudicated_claim.adjudicated_line_items:
        if item.description in non_payable_descriptions:
            total_disallowed_IRDAI += item.allowed_amount
            item.allowed_amount = 0.0
            item.disallowed_amount = item.total_amount
            item.reason = "Non-payable item as per IRDAI guidelines."
            # item.status = "Disallowed"

    if total_disallowed_IRDAI > 0.0:
        adjudicated_claim.adjustments_log.append(
            f"Items disallowed as per IRDAI non-payable list: -₹{total_disallowed_IRDAI:,.2f}"
        )
    perf_metrics["time_irda_filter_sec"] = time.monotonic() - step1_start_time

    # --- Step 2: Find Matching Sub-Limit Rules ---
    step2_start_time = time.monotonic()
    sub_limits = policy.get("sub_limits", {})
    items_to_process = [
        item
        for item in adjudicated_claim.adjudicated_line_items
        if item.status != "Disallowed"
    ]
    match_tasks = [
        get_rule_match_with_llm(item.description, sub_limits)
        for item in items_to_process
    ]
    matched_rule_names = await asyncio.gather(*match_tasks)
    perf_metrics["time_rule_matching_sec"] = time.monotonic() - step2_start_time

    # --- Step 3: Apply Matched Rules ---
    step3_start_time = time.monotonic()
    sum_insured = policy["sum_insured"]
    update_tasks = []
    final_adjudicated_items = []

    for item, rule_name in zip(items_to_process, matched_rule_names):
        if rule_name and rule_name in sub_limits:
            policy_rule_to_apply = sub_limits[rule_name]
            update_tasks.append(
                apply_policy_rule_with_llm_tools(
                    item, policy_rule_to_apply, sum_insured
                )
            )
        else:
            final_adjudicated_items.append(item)

    updated_items = []
    if update_tasks:
        updated_items = await asyncio.gather(*update_tasks)
        final_adjudicated_items.extend(updated_items)
    # add the adjustment log for the policy disallowed amount
    for updated_item in updated_items:
        if updated_item.disallowed_amount > 0.0 and updated_item.reason:
            adjudicated_claim.adjustments_log.append(
                f"Item '{updated_item.description}' disallowed: -₹{updated_item.disallowed_amount:,.2f} ({updated_item.reason})"
            )

    perf_metrics["rules_applied_count"] = len(updated_items)
    perf_metrics["time_rule_application_sec"] = time.monotonic() - step3_start_time

    # Re-assemble the full list of items
    disallowed_items = [
        item
        for item in adjudicated_claim.adjudicated_line_items
        if item.status == "Disallowed"
    ]
    final_adjudicated_items.extend(disallowed_items)
    adjudicated_claim.adjudicated_line_items = final_adjudicated_items

    # --- Step 4: Final Calculations & Claim-Level Rules ---
    final_total_allowed = sum(
        item.allowed_amount for item in adjudicated_claim.adjudicated_line_items
    )
    adjudicated_claim.total_allowed_amount = final_total_allowed

    co_payment_percentage = policy.get("co_payment_percentage", 0)
    if co_payment_percentage > 0:
        co_payment_amount = (final_total_allowed * co_payment_percentage) / 100
        adjudicated_claim.adjustments_log.append(
            f"Applied {co_payment_percentage}% co-payment: -₹{co_payment_amount:,.2f}"
        )
        final_total_allowed -= co_payment_amount

    final_payable = min(final_total_allowed, sum_insured)
    if final_payable < final_total_allowed:
        adjudicated_claim.adjustments_log.append(
            f"Final amount capped at Sum Insured of ₹{sum_insured:,.2f}."
        )
    adjudicated_claim.total_allowed_amount = final_payable

    # --- Step 5: Final AI Sanity Check ---
    step5_start_time = time.monotonic()
    sanity_result = await run_final_sanity_check(adjudicated_claim)
    adjudicated_claim.sanity_check_result = sanity_result
    perf_metrics["time_sanity_check_sec"] = time.monotonic() - step5_start_time

    # Final total time for adjudication
    perf_metrics["adjudicate_processing_time_sec"] = (
        time.monotonic() - total_adjudication_start_time
    )

    print("--- ✅ Adjudication and Final Audit Complete ---")
    return adjudicated_claim, perf_metrics
