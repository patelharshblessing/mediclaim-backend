import os
import sys

# Add the root project directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# --- Define All Test Cases ---
# (Include the TEST_CASES list here)
import asyncio

from app.pydantic_schemas import AdjudicatedLineItem
from app.rules_utils import apply_policy_rule_with_llm_tools

TEST_CASES = [
    # --- Fixed Limit Rules ---
    {
        "name": "Test 1: Fixed Limit - Capping Occurs",
        "item": AdjudicatedLineItem(
            description="Ambulance Charges",
            quantity=1,
            unit_price=4500,
            total_amount=4500,
            status="Allowed",
            allowed_amount=4500,
            disallowed_amount=0,
        ),
        "rule": {
            "type": "fixed",
            "value": 3000,
            "description": "Ambulance charges capped at Rs. 3,000.",
        },
        "sum_insured": 100000,
    },
    {
        "name": "Test 2: Fixed Limit - Under Limit (No Change Expected)",
        "item": AdjudicatedLineItem(
            description="Ambulance Charges",
            quantity=1,
            unit_price=2000,
            total_amount=2000,
            status="Allowed",
            allowed_amount=2000,
            disallowed_amount=0,
        ),
        "rule": {
            "type": "fixed",
            "value": 3000,
            "description": "Ambulance charges capped at Rs. 3,000.",
        },
        "sum_insured": 100000,
    },
    {
        "name": "Test 3: Fixed Limit - Item Already Disallowed",
        "item": AdjudicatedLineItem(
            description="Ambulance Charges",
            quantity=1,
            unit_price=5000,
            total_amount=5000,
            status="Disallowed",
            allowed_amount=0,
            disallowed_amount=5000,
        ),
        "rule": {
            "type": "fixed",
            "value": 3000,
            "description": "Ambulance charges capped at Rs. 3,000.",
        },
        "sum_insured": 100000,
    },
    # --- Percentage Limit Rules ---
    {
        "name": "Test 4: Percentage Limit - Capping Occurs",
        "item": AdjudicatedLineItem(
            description="Room Rent",
            quantity=1,
            unit_price=30000,
            total_amount=30000,
            status="Allowed",
            allowed_amount=30000,
            disallowed_amount=0,
        ),
        "rule": {
            "type": "percentage_of_sum_insured",
            "value": 1,
            "description": "Room Rent capped at 1% of Sum Insured.",
        },
        "sum_insured": 100000,
    },
    {
        "name": "Test 5: Percentage Limit - Under Limit (No Change Expected)",
        "item": AdjudicatedLineItem(
            description="Room Rent",
            quantity=1,
            unit_price=500,
            total_amount=500,
            status="Allowed",
            allowed_amount=500,
            disallowed_amount=0,
        ),
        "rule": {
            "type": "percentage_of_sum_insured",
            "value": 1,
            "description": "Room Rent capped at 1% of Sum Insured.",
        },
        "sum_insured": 100000,
    },
    # --- Edge Cases ---
    {
        "name": "Test 6: Zero Total Amount",
        "item": AdjudicatedLineItem(
            description="Room Rent",
            quantity=1,
            unit_price=0,
            total_amount=0,
            status="Allowed",
            allowed_amount=0,
            disallowed_amount=0,
        ),
        "rule": {
            "type": "fixed",
            "value": 3000,
            "description": "Room Rent capped at Rs. 3,000.",
        },
        "sum_insured": 100000,
    },
    {
        "name": "Test 7: Negative Total Amount",
        "item": AdjudicatedLineItem(
            description="Room Rent",
            quantity=1,
            unit_price=500,
            total_amount=500,
            status="Allowed",
            allowed_amount=500,
            disallowed_amount=0,
        ),
        "rule": {
            "type": "fixed",
            "value": 3000,
            "description": "Room Rent capped at Rs. 3,000.",
        },
        "sum_insured": 100000,
    },
    # --- Complex Rules ---
    {
        "name": "Test 8: Complex Rule - Surgeon Fees",
        "item": AdjudicatedLineItem(
            description="Surgeon Fees",
            quantity=1,
            unit_price=50000,
            total_amount=50000,
            status="Allowed",
            allowed_amount=50000,
            disallowed_amount=0,
        ),
        "rule": {
            "type": "percentage_of_surgery_cost",
            "value": 25,
            "description": "Surgeon fees capped at 25% of surgery cost.",
        },
        "sum_insured": 200000,
    },
    {
        "name": "Test 9: Complex Rule - Anesthetist Fees",
        "item": AdjudicatedLineItem(
            description="Anesthetist Fees",
            quantity=1,
            unit_price=15000,
            total_amount=15000,
            status="Allowed",
            allowed_amount=15000,
            disallowed_amount=0,
        ),
        "rule": {
            "type": "percentage_of_surgeon_fee",
            "value": 30,
            "description": "Anesthetist fees capped at 30% of surgeon fees.",
        },
        "sum_insured": 200000,
    },
    # Add more test cases as needed...
]

# --- Define All Test Cases ---
# (Include the TEST_CASES list here)


async def run_all_tests():
    """
    Runs all defined test cases against the LLM agent.
    """
    for i, case in enumerate(TEST_CASES):
        print(f"\n--- Running Test Case #{i+1}: {case['name']} ---")

        try:
            result = await apply_policy_rule_with_llm_tools(
                item=case["item"],
                policy_rule=case["rule"],
                sum_insured=case["sum_insured"],
            )
            # The agent's final output is in the 'output' key
            print(f"Agent's Final Answer:\n{result}")

        except Exception as e:
            print(f"\n--- ❌ Test Case Failed with Error ---")
            print(f"An unexpected error occurred: {e}")

        print("-" * 50)


# --- Main execution block ---
if __name__ == "__main__":
    asyncio.run(run_all_tests())
