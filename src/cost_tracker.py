"""
Cost and Token Tracker for Gemini API calls across Orchestrator, Generator, QC Inspector, and Visual Critic.
Calculates exact real-time costs based on Vertex AI / Gemini API pricing tiers.
"""

from typing import Dict, Any, Optional

# Pricing rates per 1,000,000 tokens in USD
PRICING_TIERS = {
    # Gemini 3.7 Flash & 3.6 Flash text / multimodal
    "gemini-3.7-flash": {
        "input_per_million": 0.075,
        "cached_per_million": 0.01875,
        "output_per_million": 0.30,
        "image_output_flat": 0.0
    },
    "gemini-3.6-flash": {
        "input_per_million": 0.075,
        "cached_per_million": 0.01875,
        "output_per_million": 0.30,
        "image_output_flat": 0.0
    },
    # Gemini 3.1 Flash Image (4K Native)
    "gemini-3.1-flash-image": {
        "input_per_million": 0.075,
        "cached_per_million": 0.01875,
        "output_per_million": 0.30,
        "image_output_flat": 0.030  # $0.030 per generated 4K image master
    },
    # Default fallback tier
    "default": {
        "input_per_million": 0.075,
        "cached_per_million": 0.01875,
        "output_per_million": 0.30,
        "image_output_flat": 0.030
    }
}


def calculate_step_cost(model_name: str, usage_metadata: Any, is_image_gen: bool = False) -> Dict[str, Any]:
    """Calculates cost and token metrics from a single Gemini generate_content response."""
    if not usage_metadata:
        return {
            "model": model_name,
            "prompt_tokens": 0,
            "candidates_tokens": 0,
            "cached_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.030 if is_image_gen else 0.0005,
            "formatted_cost": "$0.0300" if is_image_gen else "$0.0005"
        }

    tier = PRICING_TIERS.get(model_name, PRICING_TIERS["default"])

    prompt_tokens = getattr(usage_metadata, "prompt_token_count", 0) or 0
    candidates_tokens = getattr(usage_metadata, "candidates_token_count", 0) or 0
    cached_tokens = getattr(usage_metadata, "cached_content_token_count", 0) or 0
    total_tokens = getattr(usage_metadata, "total_token_count", 0) or (prompt_tokens + candidates_tokens)

    # Calculate input cost (accounting for cached tokens discount)
    uncached_prompt_tokens = max(0, prompt_tokens - cached_tokens)
    input_cost = (uncached_prompt_tokens / 1_000_000.0) * tier["input_per_million"]
    cached_cost = (cached_tokens / 1_000_000.0) * tier["cached_per_million"]

    # Calculate output cost
    output_cost = 0.0
    if is_image_gen or tier["image_output_flat"] > 0:
        # For image generation, apply flat 4K image generation rate
        output_cost = tier["image_output_flat"]
    else:
        output_cost = (candidates_tokens / 1_000_000.0) * tier["output_per_million"]

    total_cost = input_cost + cached_cost + output_cost

    return {
        "model": model_name,
        "prompt_tokens": prompt_tokens,
        "candidates_tokens": candidates_tokens,
        "cached_tokens": cached_tokens,
        "total_tokens": total_tokens,
        "cost_usd": round(total_cost, 6),
        "formatted_cost": f"${total_cost:.4f}"
    }


def aggregate_costs(step_costs: list) -> Dict[str, Any]:
    """Combines multiple step cost records into a single aggregated summary."""
    total_prompt = sum(s.get("prompt_tokens", 0) for s in step_costs)
    total_candidates = sum(s.get("candidates_tokens", 0) for s in step_costs)
    total_cached = sum(s.get("cached_tokens", 0) for s in step_costs)
    total_tokens = sum(s.get("total_tokens", 0) for s in step_costs)
    total_cost_usd = sum(s.get("cost_usd", 0.0) for s in step_costs)

    return {
        "prompt_tokens": total_prompt,
        "candidates_tokens": total_candidates,
        "cached_tokens": total_cached,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost_usd, 6),
        "formatted_total_cost": f"${total_cost_usd:.4f}",
        "steps": step_costs
    }
