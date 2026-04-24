"""Chat API for conversational retrieval."""

from pathlib import Path
from typing import Any
import json
import uuid
from datetime import datetime


def get_chat_history_path(workspace_root: str) -> Path:
    """Get the path to the chat history directory."""
    path = Path(workspace_root) / ".chat_history"
    path.mkdir(exist_ok=True)
    return path


def load_chat_sessions(workspace_root: str) -> list[dict[str, Any]]:
    """Load all chat sessions."""
    history_path = get_chat_history_path(workspace_root)
    sessions = []

    for session_file in history_path.glob("*.json"):
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                session = json.load(f)
                sessions.append(session)
        except Exception:
            continue

    # Sort by created_at descending
    sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return sessions


def create_chat_session(workspace_root: str, source_name: str) -> dict[str, Any]:
    """Create a new chat session."""
    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "source_name": source_name,
        "created_at": datetime.now().isoformat(),
        "messages": [],
    }

    history_path = get_chat_history_path(workspace_root)
    session_file = history_path / f"{session_id}.json"

    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2, ensure_ascii=False)

    return session


def load_chat_session(workspace_root: str, session_id: str) -> dict[str, Any]:
    """Load a specific chat session."""
    history_path = get_chat_history_path(workspace_root)
    session_file = history_path / f"{session_id}.json"

    if not session_file.exists():
        raise ValueError(f"Session not found: {session_id}")

    with open(session_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_chat_session(workspace_root: str, session: dict[str, Any]) -> None:
    """Save a chat session."""
    history_path = get_chat_history_path(workspace_root)
    session_id = session.get("session_id")
    if not session_id:
        raise ValueError("Session ID is required")

    session_file = history_path / f"{session_id}.json"

    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2, ensure_ascii=False)


def chat_with_source(
    workspace_root: str,
    session_id: str,
    message: str,
    model_config: dict[str, Any],
) -> dict[str, Any]:
    """Send a message and get a response using the configured model."""
    from apps.portal_runner.retrieval_api import RetrievalAPI

    # Load session
    session = load_chat_session(workspace_root, session_id)
    source_name = session.get("source_name")

    if not source_name:
        raise ValueError("Source name not found in session")

    # Perform retrieval
    retrieval_api = RetrievalAPI(workspace_root)
    search_results = retrieval_api.search(
        source_name=source_name,
        query=message,
        strategy="hybrid",
        top_k=5,
    )

    # Build context from search results
    context_parts = []
    sources = []

    for i, result in enumerate(search_results.get("results", [])[:5], 1):
        content = result.get("content", "")
        metadata = result.get("metadata", {})
        score = result.get("score", 0)

        context_parts.append(f"[Document {i}]\n{content}\n")
        sources.append({
            "index": i,
            "content": content[:200] + "..." if len(content) > 200 else content,
            "metadata": metadata,
            "score": score,
        })

    context = "\n".join(context_parts)

    # Build prompt
    prompt = f"""Based on the following documents, please answer the user's question.

Documents:
{context}

User Question: {message}

Please provide a clear and concise answer based on the documents above. If the documents don't contain enough information to answer the question, please say so."""

    # Call LLM
    try:
        response_text = call_llm(model_config, prompt)
    except Exception as e:
        response_text = f"Error calling LLM: {str(e)}"

    # Add messages to session
    user_message = {
        "role": "user",
        "content": message,
        "timestamp": datetime.now().isoformat(),
    }

    assistant_message = {
        "role": "assistant",
        "content": response_text,
        "sources": sources,
        "timestamp": datetime.now().isoformat(),
    }

    session["messages"].append(user_message)
    session["messages"].append(assistant_message)

    # Save session
    save_chat_session(workspace_root, session)

    return {
        "message": assistant_message,
        "sources": sources,
    }


def call_llm(model_config: dict[str, Any], prompt: str) -> str:
    """Call the configured LLM with the given prompt."""
    import requests

    provider = model_config.get("provider", "ollama")
    base_url = model_config.get("base_url", "")
    model_name = model_config.get("model_name", "")
    temperature = model_config.get("temperature", 0.7)
    max_tokens = model_config.get("max_tokens", 2000)

    if provider == "ollama":
        # Call Ollama API
        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json().get("response", "")

    elif provider == "lmstudio":
        # Call LM Studio API (OpenAI-compatible)
        api_key = model_config.get("api_key", "lm-studio")
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    elif provider == "openai":
        # Call OpenAI API
        api_key = model_config.get("api_key", "")
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    else:
        raise ValueError(f"Unsupported provider: {provider}")
