from dspy import LM


def setup_dspy(
    model: str = "groq/llama-3.1-8b-instant",
    api_key: str = None,
    max_tokens: int = 256,
    temperature: float = 0,
) -> LM:
    """Creates and returns a DSPy language model without configuring global settings.

    Args:
        model: The LiteLLM model route to use, such as openai/gpt-4o-mini
            gemini/gemini-2.5-flash-lite, or groq/llama-3.1-8b-instant.
        api_key: Provider API key.
        max_tokens: Maximum tokens for response.
        temperature: Sampling temperature 0.0-2.0 (default: 0.3)
                    Higher values = more random, lower = more deterministic
    """

    lm = LM(model, api_key=api_key, max_tokens=max_tokens, temperature=temperature)
    return lm
