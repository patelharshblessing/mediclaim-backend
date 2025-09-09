import asyncio
import os
import sys

# Add the root project directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    # Assuming your function is in a file named 'llm_tool_engine.py'
    from app.rules_utils import apply_policy_rule_with_llm_tools
    from app.pydantic_schemas import AdjudicatedLineItem
except (ImportError, FileNotFoundError) as e:
    print(f"\nERROR: Could not import modules. Check file names and paths.")
    print(f"Details: {e}")
    sys.exit(1)

# --- Define All Test Cases ---
# A list of dictionaries, where each dictionary is a complete test case.
TEST_CASES = [
    # {
    #     "name": "Test 1: Fixed Limit - Capping Occurs",
    #     "item": AdjudicatedLineItem(description="Ambulance Charges", quantity=1, unit_price=4500, total_amount=4500, status="Allowed", allowed_amount=4500, disallowed_amount=0),
    #     "rule": {"type": "fixed", "value": 3000, "per": "hospitalization", "description": "Ambulance charges capped at Rs. 3,000."},
    # },
    # {
    #     "name": "Test 2: Fixed Limit - Under Limit (No Change Expected)",
    #     "item": AdjudicatedLineItem(description="Ambulance Charges", quantity=1, unit_price=2000, total_amount=2000, status="Allowed", allowed_amount=2000, disallowed_amount=0),
    #     "rule": {"type": "fixed", "value": 3000, "per": "hospitalization", "description": "Ambulance charges capped at Rs. 3,000."},
    # },
    # {
    #     "name": "Test 3: Item Already Disallowed (No Change Expected)",
    #     "item": AdjudicatedLineItem(description="Disposable Gown", quantity=1, unit_price=500, total_amount=500, status="Disallowed", allowed_amount=0, disallowed_amount=500),
    #     "rule": {"type": "fixed", "value": 100, "description": "A rule for gowns."},
    # },
    # {
    #     "name": "Test 4: Fixed Limit - ICU Charges",
    #     "item": AdjudicatedLineItem(description="ICU Charges", quantity=1, unit_price=20000, total_amount=20000, status="Allowed", allowed_amount=20000, disallowed_amount=0),
    #     "rule": {"type": "fixed", "value": 15000, "description": "ICU charges are capped at a maximum of Rs. 15,000 per day."},
    # },
    {
        "name": "Test 5: Percentage Limit - (Testing Agent's Handling of Missing Info)",
        "item": AdjudicatedLineItem(description="Room Rent", quantity=1, unit_price=30000, total_amount=30000, status="Allowed", allowed_amount=30000, disallowed_amount=0),
        "rule": {"type": "percentage_of_sum_insured", "value": 1, "description": "Room Rent capped at 1% of Sum Insured."},
        "sum_insured" : 100000
        # NOTE: This case intentionally omits the required 'sum_insured'.
        # We are testing how the agent responds when critical context is missing from the prompt.
    },
]

async def run_all_tests():
    """
    Runs all defined test cases against the LLM agent.
    """
    for i, case in enumerate(TEST_CASES):
        print(f"\n--- Running Test Case #{i+1}: {case['name']} ---")
        
        try:
            result = await apply_policy_rule_with_llm_tools(
                item=case['item'],
                policy_rule=case['rule'],
                sum_insured=case['sum_insured']
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