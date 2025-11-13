import dspy
from dspy import LM, ColBERTv2


def setup_dspy(
    model: str = "openai/gpt-4o-mini",
    api_key: str = None,
    max_tokens: int = 8000,
    temperature: float = 0.1,
) -> LM:
    """Creates and returns a DSPy language model without configuring global settings.

    Args:
        model: The model to use (default: openai/gpt-4o-mini)
        api_key: OpenAI API key
        max_tokens: Maximum tokens for response (default: 8000)
        temperature: Sampling temperature 0.0-2.0 (default: 0.3)
                    Higher values = more random, lower = more deterministic
    """

    lm = LM(model, api_key=api_key, max_tokens=max_tokens, temperature=temperature)
    return lm
