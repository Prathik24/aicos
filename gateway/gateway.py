import yaml
from datetime import datetime, timezone
from pathlib import Path

from core.schemas.audit import GatewayCall
from gateway.providers import ollama
from core import audit


def complete(
    task: str,
    prompt: str,
    data_class: str,
    config_path: str = "config/routing.yaml",
    schema : dict | None = None,
    prompt_version: str = "v6"
) -> str:
    """
    Routes a task to the appropriate model provider based on configuration.

    Args:
        task: Name of the task (e.g., "extraction", "smoke_test")
        prompt: The prompt to send to the model
        data_class: The data class associated with the call
        config_path: Path to the routing configuration YAML file

    Returns:
        The model's response string

    Raises:
        KeyError: If the task or tier is not found in config
        Exception: Re-raises any exception from the provider after auditing
    """
    # Load configuration
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Look up task -> tier; unknown -> raise KeyError with the task name
    if task not in config['tasks']:
        raise KeyError(f"Task '{task}' not found in routing configuration")

    tier = config['tasks'][task]['tier']

    # Look up tier -> provider, model
    if tier not in config['tiers']:
        raise KeyError(f"Tier '{tier}' not found in routing configuration")

    tier_config = config['tiers'][tier]
    provider = tier_config['provider']
    model = tier_config['model']

    # Map provider name to provider module
    provider_map = {
        'ollama': ollama,
    }

    if provider not in provider_map:
        raise ValueError(f"Provider '{provider}' is not supported")

    provider_module = provider_map[provider]

    # Try to call the provider's chat function
    timestamp = datetime.now(timezone.utc)
    exception_to_raise = None

    try:
        reply = provider_module.chat(model, prompt, format=schema)
        result = reply["content"]
        tokens_in = reply.get("tokens_in")
        tokens_out = reply.get("tokens_out")
        duration_ms = reply.get("duration_ms")
        load_ms = reply.get("load_ms")
        eval_ms = reply.get("eval_ms")
        done_reason = reply.get("done_reason")
        if tokens_in and tokens_in >= 30000:   # near the 32k window
            print(f"⚠️  WARNING: tokens_in={tokens_in} near context limit")
        outcome = "success"
        error = None
    except Exception as e:
        outcome = "failure"
        error = str(e)
        result = None
        tokens_in = tokens_out = duration_ms = load_ms = eval_ms = done_reason = None
        exception_to_raise = e

    # Build GatewayCall ONCE here (after the try/except)
    audit.append(GatewayCall(
        timestamp=timestamp,
        task=task,
        data_class=data_class,
        tier=tier,
        provider=provider,
        model=model,
        prompt_version=prompt_version,
        outcome=outcome,
        error=error,
        tokens_in = tokens_in,
        tokens_out = tokens_out,
        duration_ms = duration_ms,
        load_ms = load_ms,
        eval_ms = eval_ms,
        done_reason = done_reason,
        payload_preview=prompt[:200] if prompt else None
    ))

    # Re-raise if it failed
    if exception_to_raise:
        raise exception_to_raise

    return result
