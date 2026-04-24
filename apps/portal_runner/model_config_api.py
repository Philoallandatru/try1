"""Model Configuration API for managing LLM model settings."""

from pathlib import Path
from typing import Any
import json


def get_model_config_path(workspace_root: str) -> Path:
    """Get the path to the model configuration file."""
    return Path(workspace_root) / ".model_config.json"


def load_model_config(workspace_root: str) -> dict[str, Any]:
    """Load the current model configuration."""
    config_path = get_model_config_path(workspace_root)
    if not config_path.exists():
        return {
            "provider": "ollama",
            "model_name": "llama3.2",
            "base_url": "http://localhost:11434",
            "api_key": "",
            "temperature": 0.7,
            "max_tokens": 2000,
        }

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_model_config(workspace_root: str, config: dict[str, Any]) -> dict[str, Any]:
    """Save model configuration."""
    config_path = get_model_config_path(workspace_root)

    # Validate required fields
    required_fields = ["provider", "model_name", "base_url"]
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")

    # Save configuration
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    return {"success": True, "config": config}


def test_model_connection(workspace_root: str) -> dict[str, Any]:
    """Test the connection to the configured model."""
    config = load_model_config(workspace_root)

    try:
        import requests

        provider = config.get("provider", "ollama")
        base_url = config.get("base_url", "")

        if provider == "ollama":
            # Test Ollama connection
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name") for m in models]
                return {
                    "success": True,
                    "message": f"Connected to Ollama. Available models: {', '.join(model_names)}",
                    "available_models": model_names,
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to connect to Ollama: HTTP {response.status_code}",
                }

        elif provider == "lmstudio":
            # Test LM Studio connection
            response = requests.get(f"{base_url}/v1/models", timeout=5)
            if response.status_code == 200:
                models = response.json().get("data", [])
                model_ids = [m.get("id") for m in models]
                return {
                    "success": True,
                    "message": f"Connected to LM Studio. Available models: {', '.join(model_ids)}",
                    "available_models": model_ids,
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to connect to LM Studio: HTTP {response.status_code}",
                }

        elif provider in ["openai", "anthropic", "azure", "google"]:
            # For cloud providers, just check if API key is provided
            api_key = config.get("api_key", "")
            if not api_key:
                return {
                    "success": False,
                    "message": f"API key is required for {provider}",
                }
            return {
                "success": True,
                "message": f"Configuration looks valid for {provider}",
            }

        else:
            return {
                "success": False,
                "message": f"Unknown provider: {provider}",
            }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"Connection error: {str(e)}",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error testing connection: {str(e)}",
        }
