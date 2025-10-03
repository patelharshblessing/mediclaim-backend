# app/rules_utils.py

import operator
import os
import sys
from typing import List, Tuple

# Add the root project directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.config import settings
from app.normalization_service import NormalizationService
from app.pydantic_schemas import (
    AdjudicatedClaim,
    AdjudicatedLineItem,
    LineItem,
    PolicyRuleMatch,
    SanityCheckResult,
)

# ==============================================================================
# 1. IDENTIFY NON-PAYABLE ITEMS (Deterministic)
# ==============================================================================


def identify_non_payable_items(
    line_items: list[LineItem], service: NormalizationService
) -> list[LineItem]:
    """Identifies and returns a list of line items that are categorized as non-payable."""
    non_payable_items_found = []
    for item in line_items:
        normalized_item = service.normalize_description(description=item.description)
        if normalized_item and normalized_item["category"] == "Non-Payable Item":
            non_payable_items_found.append(item)
    return non_payable_items_found


# ==============================================================================
# 2. RULE MATCHING (with Fallback)
# ==============================================================================

# --- LLM Clients for Rule Matching ---
gemini_match_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.GEMINI_API_KEY,
    convert_system_message_to_human=True,
)
structured_gemini_match = gemini_match_llm.with_structured_output(PolicyRuleMatch)

openai_match_llm = ChatOpenAI(model="gpt-4o", openai_api_key=settings.OPENAI_API_KEY)
structured_openai_match = openai_match_llm.with_structured_output(PolicyRuleMatch)


async def get_rule_match_with_llm(
    item_description: str, sub_limits: dict
) -> str | None:
    """Uses LLM to find a matching rule, with a fallback from Gemini to GPT-5."""
    list_of_rule_names = [k for k, v in sub_limits.items() if v is not None]
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

    try:
        print(f"Attempting rule match for '{item_description}' with Gemini...")
        chain = prompt | structured_gemini_match
        response = await chain.ainvoke(
            {
                "item_description": item_description,
                "list_of_rule_names": list_of_rule_names,
            }
        )
    except Exception as e:
        print(f"Gemini rule match failed: {e}. Falling back to GPT-5.")
        chain = prompt | structured_openai_match
        response = await chain.ainvoke(
            {
                "item_description": item_description,
                "list_of_rule_names": list_of_rule_names,
            }
        )

    if response and response.applicable_rule_name:
        return response.applicable_rule_name
    return None


# ==============================================================================
# 3. RULE APPLICATION (with Fallback)
# ==============================================================================


# --- Agent Tools (Model-Agnostic) ---
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


tools = [multiply, divide, add, subtract, percentage]

# --- Agent Prompt (Model-Agnostic) ---
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

# --- Agent and Formatter Setup ---
gemini_agent_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro", google_api_key=settings.GEMINI_API_KEY, temperature=0.0
)
gemini_agent = create_tool_calling_agent(gemini_agent_llm, tools, AGENT_PROMPT)
gemini_agent_executor = AgentExecutor(
    agent=gemini_agent, tools=tools, verbose=True
).with_retry()
gemini_formatter = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", google_api_key=settings.GEMINI_API_KEY, temperature=0.0
)
structured_gemini_final = gemini_formatter.with_structured_output(AdjudicatedLineItem)

openai_agent_llm = ChatOpenAI(
    model="gpt-4o", openai_api_key=settings.OPENAI_API_KEY, temperature=0.0
)
openai_agent = create_tool_calling_agent(openai_agent_llm, tools, AGENT_PROMPT)
openai_agent_executor = AgentExecutor(
    agent=openai_agent, tools=tools, verbose=True
).with_retry()
openai_formatter = ChatOpenAI(
    model="gpt-4o", openai_api_key=settings.OPENAI_API_KEY, temperature=0.0
)
structured_openai_final = openai_formatter.with_structured_output(AdjudicatedLineItem)


async def apply_policy_rule_with_llm_tools(
    item: AdjudicatedLineItem, policy_rule: dict, sum_insured: float
) -> AdjudicatedLineItem:
    """Uses a tool-based agent to apply a rule, with a fallback from Gemini to GPT-5."""
    if item.status == "Disallowed":
        return item
    input_prompt = f"- Current Line Item: {item.model_dump_json()}\n- Policy Rule to Apply: {policy_rule}\n- Total sum insured: {sum_insured}"

    try:
        print(
            f"Attempting rule application for '{item.description}' with Gemini agent..."
        )
        result = await gemini_agent_executor.ainvoke({"input": input_prompt})
        format_prompt = f"Format the following text into the specified structure: {result['output']}"
        final_result = await structured_gemini_final.ainvoke(format_prompt)
    except Exception as e:
        print(f"Gemini agent failed: {e}. Falling back to GPT-5 agent.")
        result = await openai_agent_executor.ainvoke({"input": input_prompt})
        format_prompt = f"Format the following text into the specified structure: {result['output']}"
        final_result = await structured_openai_final.ainvoke(format_prompt)

    return final_result


# ==============================================================================
# 4. SANITY CHECK (with Fallback)
# ==============================================================================

FLAG_CATEGORIES = [
    "Calculation Error",
    "Logic Inconsistency",
    "High Cost Anomaly",
    "Missing Information",
    "Policy Misinterpretation",
]

# --- LLM Clients for Sanity Check ---
gemini_sanity_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro", google_api_key=settings.GEMINI_API_KEY, temperature=0.0
)
gemini_sanity_formatter = gemini_sanity_llm.with_structured_output(SanityCheckResult)

openai_sanity_llm = ChatOpenAI(
    model="gpt-4o", openai_api_key=settings.OPENAI_API_KEY, temperature=0.0
)
openai_sanity_formatter = openai_sanity_llm.with_structured_output(SanityCheckResult)


async def run_final_sanity_check(
    adjudicated_claim: AdjudicatedClaim,
) -> SanityCheckResult:
    """Performs a final sanity check, with a fallback from Gemini to GPT-5."""
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
    3.  Third, if `is_reasonable` is `false`, you MUST select one or more relevant flags from the `Predefined Flag Categories` list and add them to the `flags` array. If everything is reasonable, the `flags` array should be empty.

    Respond ONLY with a valid JSON object following the specified schema.
    ---
    """

    try:
        print("Attempting sanity check with Gemini...")
        response = await gemini_sanity_formatter.ainvoke(input_prompt)
    except Exception as e:
        print(f"Gemini sanity check failed: {e}. Falling back to GPT-5.")
        response = await openai_sanity_formatter.ainvoke(input_prompt)

    return response