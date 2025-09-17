# import os
# import sys
# # Add the root project directory to the Python path
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '...')))
# from app.pydantic_schemas import AdjudicatedLineItem, LineItem
# from app.normalization_service import NormalizationService
# from langchain_openai import ChatOpenAI
# from app.pydantic_schemas import PolicyRuleMatch
# import operator
# from datetime import date
# from typing import Tuple

# from langchain.agents import AgentExecutor, create_openai_tools_agent
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.tools import tool

# from app.config import settings


# OPENAI_API_KEY = settings.OPENAI_API_KEY

# #returns the list of line items that are non-payable
# # based on the IRDAI guidelines
# def identify_non_payable_items(
#     line_items: list[LineItem],
#     service: NormalizationService  # <-- The service is PASSED IN as an argument
# ) -> list[LineItem]:
#     """
#     Identifies and returns a list of line items that are categorized as non-payable.
#     """
#     non_payable_items_found = []
#     for item in line_items:
#         # It now uses the service that was passed in
#         normalized_item = service.normalize_description(description=item.description)

#         if normalized_item and normalized_item['category'] == "Non-Payable Item":
#             non_payable_items_found.append(item)

#     return non_payable_items_found


# # this function finds the rule that matches the item description using the LLM
# # and returns the rule name if it exists in the sub_limits
# # otherwise returns None


# # --- The Prompt Template ---
# PROMPT_TEMPLATE = """
# You are an expert insurance adjudicator. Your task is to match a medical bill item to a specific policy rule.

# **Medical Item Description:** "{item_description}"

# **Available Policy Rules:** {list_of_rule_names}

# Which of the 'Available Policy Rules' is the most direct and appropriate match for the 'Medical Item Description'?

# Respond ONLY with a valid JSON object in the following format:
# {{"applicable_rule_name": "Name of the matching rule"}}

# If no rule is a clear match, the value for "applicable_rule_name" should be null.
# """
# # Initialize the LLM with structured output
# llm= ChatOpenAI(
#     model="gpt-4o",
#     openai_api_key=OPENAI_API_KEY
# )
# structured_llm=llm.with_structured_output(PolicyRuleMatch,method="function_calling")

# async def get_rule_match_with_llm(item_description: str, sub_limits: dict) -> str | None:
#     """
#     Uses the LLM to find a rule that matches the item description.

#     Args:
#         item_description: The raw item description from the bill.
#         sub_limits: The 'sub_limits' dictionary from the policy rulebook.

#     Returns:
#         The name of the matching rule if a rule applies, otherwise None.
#     """

#     list_of_rule_names= [policy_name for policy_name in sub_limits.keys() if sub_limits[policy_name] is not None]
#     # print(f"Available Policy Rules: {list_of_rule_names_and_descriptions}")
#     # Format the prompt with the item description and available rules
#     PROMPT_TEMPLATE = f"""
#     You are an expert insurance adjudicator. Your task is to match a medical bill item to a specific policy rule.

#     **Medical Item Description:** "{item_description}"

#     **Available Policy Rules:** {list_of_rule_names}


#     Which of the 'Available Policy Rules' is the most direct and appropriate match for the 'Medical Item Description'?

#     Respond ONLY with a valid JSON object in the following format:
#     {{"applicable_rule_name": "Name of the matching rule"}}

#     If no rule is a clear match, respond with the schema provided below:
#     {{"applicable_rule_name": [str] | None}}
#     """
#     # Call the LLM with the prompt
#     response = await structured_llm.ainvoke(PROMPT_TEMPLATE)
#     print(f"LLM Response for the item : {item_description} is : {response}")
#     # Extract the rule name from the response
#     # --- FIX: Use dot notation to access the object's attribute ---
#     if response and response.applicable_rule_name:
#         return response.applicable_rule_name

#     return None


# # --- 1. Define the Tools ---
# # These are simple, 100% accurate Python functions the LLM can use.

# @tool
# def multiply(a: float, b: float) -> float:
#     """Multiplies two numbers."""
#     return operator.mul(a, b)

# @tool
# def divide(a: float, b: float) -> float:
#     """Divides two numbers."""
#     return operator.truediv(a, b)

# @tool
# def add(a: float, b: float) -> float:
#     """Adds two numbers."""
#     return operator.add(a, b)

# @tool
# def subtract(a: float, b: float) -> float:
#     """Subtracts two numbers."""
#     return operator.sub(a, b)

# @tool
# def percentage(part: float, whole: float) -> float:
#     """Calculates what 'part' percentage of 'whole' is."""
#     return (part / 100) * whole


# # --- 2. Set up the LLM Agent ---
# # We initialize the agent and its tools once for efficiency.

# tools = [multiply, divide, add, subtract, percentage]

# # Use a powerful model that is good at reasoning and tool use
# llm = ChatOpenAI(model="gpt-4o", api_key=settings.OPENAI_API_KEY, temperature=0.0)
# # The master prompt that guides the agent
# AGENT_PROMPT = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system",
#             """You are a precise and accurate insurance claims adjudication engine.
# Your task is to apply a single policy rule to a single line item and calculate the final allowed amount.
# You must use the provided tools to perform all mathematical calculations.
# Reason step-by-step to determine the correct limit and then compare it to the item's currently allowed amount.
# Finally, provide your final answer by summarizing the updated AdjudicatedLineItem.""",
#         ),
#         ("human", "Apply the policy rule to the line item based on the following context:\n{input}"),
#         ("placeholder", "{agent_scratchpad}"),
#     ]
# )

# agent = create_openai_tools_agent(llm, tools, AGENT_PROMPT)
# agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True).with_retry()


# # LLM for getting the output in the structure of AdjudicatedLineItem
# llm_str = ChatOpenAI(model="gpt-4o", api_key=settings.OPENAI_API_KEY, temperature=0.0)
# llm_structured=llm_str.with_structured_output(AdjudicatedLineItem)


# # --- 3. The Main Function ---

# async def apply_policy_rule_with_llm_tools(
#     item: AdjudicatedLineItem,
#     policy_rule: dict,
#     sum_insured: float
# ) -> AdjudicatedLineItem:
#     """
#     Uses a tool-based LLM agent to apply a flexible sub-limit rule to a line item.

#     Args:
#         item: The AdjudicatedLineItem to be processed.
#         policy_rule: The specific sub-limit rule dictionary from the policy rulebook.

#     Returns:
#         The updated AdjudicatedLineItem object.
#     """
#     if item.status == "Disallowed":
#         return item

#     # Construct the detailed input for the agent
#     input_prompt = f"""
#     - Current Line Item: {item.model_dump_json()}
#     - Policy Rule to Apply: {policy_rule}
#     - Total sum insured: {sum_insured}

#     Please perform the calculation and provide the final, updated AdjudicatedLineItem object as your answer.
#     """

#     try:
#         # Invoke the agent
#         result = await agent_executor.ainvoke({"input": input_prompt})
#         prompt=f"Your are a structure agent your task is to get the output in the format specified output: {result['output']}"
#         result=await llm_structured.ainvoke(prompt)

#         return result

#     except Exception as e:
#         print(f"An error occurred with the LLM tool agent: {e}")
#         # As requested, raise the error if the LLM fails.
#         raise


import operator
import os
import sys
from typing import Tuple

# Add the root project directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

# --- NEW: Import Gemini and the modern agent creator ---
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.normalization_service import NormalizationService
from app.pydantic_schemas import AdjudicatedLineItem, LineItem, PolicyRuleMatch

# --- Your existing functions and tools ---


# This function remains unchanged
def identify_non_payable_items(
    line_items: list[LineItem], service: NormalizationService
) -> list[LineItem]:
    """Identifies and returns a list of line items that are categorized as non-payable."""
    # ... (logic is the same)
    non_payable_items_found = []
    for item in line_items:
        normalized_item = service.normalize_description(description=item.description)
        if normalized_item and normalized_item["category"] == "Non-Payable Item":
            non_payable_items_found.append(item)
    return non_payable_items_found




# --- NEW: Initialize the Gemini LLM for structured output ---
llm_match = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.GEMINI_API_KEY,
    convert_system_message_to_human=True,  # Recommended for Gemini
)
structured_llm_match = llm_match.with_structured_output(PolicyRuleMatch)


async def get_rule_match_with_llm(
    item_description: str, sub_limits: dict
) -> str | None:
    """Uses the Gemini LLM to find a rule that matches the item description."""
    list_of_rule_names = [
        policy_name
        for policy_name in sub_limits.keys()
        if sub_limits.get(policy_name) is not None
    ]

    # Using a robust prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert insurance adjudicator. Your task is to match a medical bill item to a specific policy rule. Respond only with the name of the matching rule or null.",
            ),
            (
                "human",
                "Medical Item Description: '{item_description}'\n\nAvailable Policy Rules: {list_of_rule_names}",
            ),
        ]
    )

    chain = prompt | structured_llm_match

    response = await chain.ainvoke(
        {"item_description": item_description, "list_of_rule_names": list_of_rule_names}
    )

    print(f"LLM Response for the item : {item_description} is : {response}")
    if response and response.applicable_rule_name:
        return response.applicable_rule_name
    return None


# --- Math tools remain unchanged ---
@tool
def multiply(a: float, b: float) -> float:
    """Multiplies two numbers."""
    return operator.mul(a, b)


@tool
def divide(a: float, b: float) -> float:
    """Divides two numbers."""
    return operator.truediv(a, b)


@tool
def add(a: float, b: float) -> float:
    """Adds two numbers."""
    return operator.add(a, b)


@tool
def subtract(a: float, b: float) -> float:
    """Subtracts two numbers."""
    return operator.sub(a, b)


@tool
def percentage(part: float, whole: float) -> float:
    """Calculates what 'part' percentage of 'whole' is."""
    return (part / 100) * whole


# ... (add, subtract, divide, percentage tools are the same)

# --- NEW: Set up the Gemini Agent ---
tools = [multiply, divide, add, subtract, percentage]

# Use the Gemini model for the agent
llm_agent = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro", google_api_key=settings.GEMINI_API_KEY, temperature=0.0
)

AGENT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a meticulous and precise insurance claims adjudication engine.
Your task is to apply a single policy rule to a single line item and calculate the final allowed amount.

**CRITICAL INSTRUCTION: You MUST use the provided tools for all mathematical calculations, even for simple ones. Do NOT perform calculations yourself.**

**You must follow these steps to reason:**
1.  First, identify the **'claimed amount'**, the **'quantity'**, and the specific **'policy rule'** from the context.
2.  Second, analyze the rule. Is it a 'per day', 'per instance', 'per unit', or a total 'claim level' limit?
3.  Third, using the provided tools, calculate the **maximum possible allowed amount** based on the rule and the quantity. For 'per day' or 'per instance' rules, this will involve **multiplying the limit by the quantity**.
4.  Fourth, compare this calculated maximum with the originally claimed amount for the line item.
5.  The final **'allowed amount'** for this item is the **lesser** of these two values (the calculated maximum and the claimed amount).

Provide your final answer by summarizing the updated AdjudicatedLineItem object.
""",
        ),
        (
            "human",
            "Apply the policy rule to the line item based on the following context:\n{input}",
        ),
        ("placeholder", "{agent_scratchpad}"),
    ]
)

# Use the modern, model-agnostic agent creator
agent = create_tool_calling_agent(llm_agent, tools, AGENT_PROMPT)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True).with_retry()

# --- NEW: Set up the Gemini LLM for final formatting ---
llm_formatter = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", google_api_key=settings.GEMINI_API_KEY, temperature=0.0
)
llm_structured_final = llm_formatter.with_structured_output(AdjudicatedLineItem)


# --- The Main Function (unchanged logic, just uses the new Gemini agent) ---
async def apply_policy_rule_with_llm_tools(
    item: AdjudicatedLineItem, policy_rule: dict, sum_insured: float
) -> AdjudicatedLineItem:
    """Uses a tool-based Gemini agent to apply a flexible sub-limit rule."""
    if item.status == "Disallowed":
        return item

    input_prompt = f"""
    - Current Line Item: {item.model_dump_json()}
    - Policy Rule to Apply: {policy_rule}
    - Total sum insured: {sum_insured}

    Please perform the calculation and provide the final, updated AdjudicatedLineItem object as your answer.
    """
    try:
        # Stage 1: Invoke the reasoning agent
        result = await agent_executor.ainvoke({"input": input_prompt})

        # Stage 2: Format the output using a structured Gemini call
        prompt = f"Your are a structure agent your task is to get the output in the format specified output: {result['output']}"
        final_result = await llm_structured_final.ainvoke(prompt)

        return final_result
    except Exception as e:
        print(f"An error occurred with the LLM tool agent: {e}")
        raise


# from gemini_sdk import ChatGoogleGenerativeAI  # Assuming this is the SDK for Gemini 2.5 Pro
from app.config import settings
from app.pydantic_schemas import AdjudicatedClaim, SanityCheckResult

# Initialize the Gemini LLM
gemini_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro", google_api_key=settings.GEMINI_API_KEY, temperature=0.0
)

llm_formatter = gemini_llm.with_structured_output(SanityCheckResult)


FLAG_CATEGORIES = [
        "Calculation Error",
        "Logic Inconsistency",
        "High Cost Anomaly",
        "Missing Information",
        "Policy Misinterpretation"
    ]



async def run_final_sanity_check(
    adjudicated_claim: AdjudicatedClaim,
) -> SanityCheckResult:
    """
    Uses Gemini to perform a final sanity check on the adjudicated claim object.
    """
    FLAG_CATEGORIES = [
        "Calculation Error",
        "Logic Inconsistency",
        "High Cost Anomaly",
        "Missing Information",
        "Policy Misinterpretation"
    ]

    input_prompt = f"""
    You are a professional claims processor with over 20 years of experience.
    Your task is to perform a final sanity check on the adjudicated claim object provided below.

    Adjudicated Claim Details:
    {adjudicated_claim.model_dump_json(indent=2)}

    **Predefined Flag Categories:**
    `{FLAG_CATEGORIES}`

    ---
    **Instructions:**
    1.  First, determine if the final adjudication is reasonable and consistent. Set `is_reasonable` to `true` or `false`.
    2.  Second, provide a brief, one-sentence explanation for your decision in the `reasoning` field.
    3.  **Third, if `is_reasonable` is `false`, you MUST select one or more relevant flags from the `Predefined Flag Categories` list and add them to the `flags` array.** If everything is reasonable, the `flags` array should be empty.

    Respond ONLY with a valid JSON object following the specified schema.
    ---
    """

    # Invoke the Gemini LLM
    response = await llm_formatter.ainvoke(input_prompt)
    print(f"Sanity Check LLM Response: {response}")

    return response
