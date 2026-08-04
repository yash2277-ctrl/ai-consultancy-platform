"""
AI Consulting Agents — Three-agent pipeline using g4f (GPT4Free):
  1. FinancialAnalyst   — deep financial analysis (McKinsey-grade)
  2. MarketStrategist   — market & competitive strategy (BCG-grade)
  3. ExecutivePartner   — synthesis & recommendations (Bain-grade)
"""

import json
import logging
import re
import asyncio
from typing import Any, Dict

from g4f.client import AsyncClient
from g4f.Provider import PollinationsAI

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# ── g4f async client (using PollinationsAI — reliable, no API key) ──────────

_client = AsyncClient(provider=PollinationsAI)


# ── JSON Extraction Helper ──────────────────────────────────────────────────

def extract_json_string(text: str) -> str:
    """
    LLMs sometimes wrap JSON in ```json ... ```.  Strip that.
    """
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Also try to find first { ... } block
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        return brace_match.group(0).strip()
    return text.strip()


# ── Retry wrapper ────────────────────────────────────────────────────────────

async def _invoke_with_retry(
    messages: list,
    max_retries: int = 3,
) -> str:
    """Invoke g4f with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            response = await _client.chat.completions.create(
                model="openai",
                messages=messages,
            )
            content = response.choices[0].message.content
            if content:
                return content
            raise ValueError("Empty response from g4f")
        except Exception as exc:
            wait = 2 ** attempt
            logger.warning(
                "g4f call attempt %d/%d failed: %s — retrying in %ds",
                attempt + 1, max_retries, exc, wait,
            )
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(wait)
    raise RuntimeError("Unexpected: retries exhausted without raising")


# ═════════════════════════════════════════════════════════════════════════════
#  AGENT 1 — Financial Analyst
# ═════════════════════════════════════════════════════════════════════════════

FINANCIAL_SYSTEM_PROMPT = """You are a **Senior Financial Analyst** at a top-tier management consultancy (McKinsey & Company calibre).

Your mandate:
- Perform rigorous, data-driven financial analysis grounded in the provided documents and industry context.
- Apply frameworks: DCF principles, DuPont decomposition, unit economics, margin waterfall analysis, working-capital efficiency, ROIC trees, and scenario modelling.
- Quantify findings wherever possible (percentages, ratios, absolute values).
- Identify financial risks, opportunities, and critical assumptions.

OUTPUT FORMAT — respond with **valid JSON only**, no surrounding text:
{
  "revenue_analysis": "...",
  "cost_structure": "...",
  "profitability_assessment": "...",
  "cash_flow_insights": "...",
  "key_financial_ratios": {"ratio_name": "value or assessment", ...},
  "risk_factors": ["...", "..."],
  "opportunities": ["...", "..."],
  "recommendations": ["...", "..."],
  "raw_analysis": "Full narrative analysis (2-4 paragraphs)"
}"""


async def run_financial_analyst(context: str, goal: str) -> Dict[str, Any]:
    """Run the Financial Analyst agent."""
    messages = [
        {"role": "system", "content": FINANCIAL_SYSTEM_PROMPT},
        {"role": "user", "content": f"""## Business Objective
{goal}

## Available Data & Context
{context}

Perform a comprehensive financial analysis addressing the business objective above. Ground your analysis in the provided data. Where data is limited, state assumptions clearly and use industry benchmarks."""},
    ]

    raw = await _invoke_with_retry(messages)
    try:
        cleaned = extract_json_string(raw)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Financial agent returned non-JSON; wrapping raw text")
        return {"raw_analysis": raw, "recommendations": []}


# ═════════════════════════════════════════════════════════════════════════════
#  AGENT 2 — Market Strategist
# ═════════════════════════════════════════════════════════════════════════════

MARKET_SYSTEM_PROMPT = """You are a **Senior Market Strategist** at a top-tier strategy consultancy (BCG calibre).

Your mandate:
- Conduct thorough market & competitive analysis using the provided context.
- Apply frameworks: Porter's Five Forces, value-chain analysis, market sizing (TAM/SAM/SOM), competitive positioning maps, Blue Ocean strategy canvas, PESTEL, and growth-share matrix.
- Identify market trends, competitive dynamics, customer segments, and white-space opportunities.
- Be specific and actionable — avoid generic platitudes.

OUTPUT FORMAT — respond with **valid JSON only**, no surrounding text:
{
  "market_overview": "...",
  "market_size_assessment": "...",
  "competitive_landscape": ["...", "..."],
  "key_trends": ["...", "..."],
  "customer_segments": ["...", "..."],
  "growth_opportunities": ["...", "..."],
  "threats": ["...", "..."],
  "strategic_positioning": "...",
  "recommendations": ["...", "..."],
  "raw_analysis": "Full narrative analysis (2-4 paragraphs)"
}"""


async def run_market_strategist(context: str, goal: str) -> Dict[str, Any]:
    """Run the Market Strategist agent."""
    messages = [
        {"role": "system", "content": MARKET_SYSTEM_PROMPT},
        {"role": "user", "content": f"""## Business Objective
{goal}

## Available Data & Context
{context}

Deliver a comprehensive market and competitive strategy analysis. Ground your insights in the provided data. Where data is limited, use your expert knowledge of market dynamics and state assumptions clearly."""},
    ]

    raw = await _invoke_with_retry(messages)
    try:
        cleaned = extract_json_string(raw)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Market agent returned non-JSON; wrapping raw text")
        return {"raw_analysis": raw, "recommendations": []}


# ═════════════════════════════════════════════════════════════════════════════
#  AGENT 3 — Executive Partner (Synthesis)
# ═════════════════════════════════════════════════════════════════════════════

EXECUTIVE_SYSTEM_PROMPT = """You are the **Managing Partner** at a top-tier management consultancy (Bain & Company calibre).

You have received analyses from your Financial Analyst and Market Strategist. Your role:
- Synthesise both analyses into a unified, executive-ready strategic recommendation.
- Apply the Pyramid Principle: lead with the answer, then supporting evidence.
- Provide a clear situation assessment, key findings, prioritised recommendations, and an implementation roadmap.
- Assign a confidence score (0-1) reflecting data completeness and analytical certainty.

OUTPUT FORMAT — respond with **valid JSON only**, no surrounding text:
{
  "situation_assessment": "...",
  "key_findings": ["...", "..."],
  "strategic_recommendations": ["...", "..."],
  "priority_actions": [
    {"action": "...", "timeframe": "...", "impact": "high/medium/low", "owner": "..."},
    ...
  ],
  "risk_matrix": [
    {"risk": "...", "likelihood": "high/medium/low", "impact": "high/medium/low", "mitigation": "..."},
    ...
  ],
  "implementation_timeline": [
    {"phase": "...", "duration": "...", "deliverables": "..."},
    ...
  ],
  "confidence_score": 0.0
}"""


async def run_executive_partner(
    context: str,
    goal_statement: str,
    financial_analysis: Dict[str, Any],
    market_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """Run the Executive Partner synthesis agent."""
    # Format sub-analyses for the executive
    fin_text = json.dumps(financial_analysis, indent=2, default=str)
    mkt_text = json.dumps(market_analysis, indent=2, default=str)

    messages = [
        {"role": "system", "content": EXECUTIVE_SYSTEM_PROMPT},
        {"role": "user", "content": f"""## Client Objective
{goal_statement}

## Source Data Context
{context[:3000]}

## Financial Analysis (from your Financial Analyst team)
{fin_text}

## Market & Competitive Analysis (from your Market Strategist team)
{mkt_text}

Synthesise these inputs into a cohesive, executive-ready strategic recommendation. Be decisive, specific, and actionable."""},
    ]

    raw = await _invoke_with_retry(messages)
    try:
        cleaned = extract_json_string(raw)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Executive agent returned non-JSON; wrapping raw text")
        return {
            "situation_assessment": raw,
            "key_findings": [],
            "strategic_recommendations": [],
            "confidence_score": 0.5,
        }
