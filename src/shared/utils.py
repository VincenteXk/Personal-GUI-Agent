"""Shared utility functions for the project."""

from openai import OpenAI


def check_model_api(base_url: str, model_name: str, api_key: str = "EMPTY") -> bool:
    """
    Check if the model API is accessible and the specified model exists.

    Checks:
    1. Network connectivity to the API endpoint
    2. Model exists in the available models list

    Args:
        base_url: The API base URL (e.g., "http://localhost:8000/v1")
        model_name: The model name to check
        api_key: The API key (default: "EMPTY")

    Returns:
        bool: True if API is accessible and model exists, False otherwise
    """
    print("🔍 Checking model API...")
    print("-" * 50)

    all_passed = True

    # Check 1: Network connectivity using chat API
    print(f"1. Checking API connectivity ({base_url})...", end=" ")
    # Create OpenAI client
    client = OpenAI(base_url=base_url, api_key=api_key, timeout=30.0)

    # Use chat completion to test connectivity (more universally supported than /models)
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=5,
        temperature=0.0,
        stream=False,
    )

    # Check if we got a valid response
    if response.choices and len(response.choices) > 0:
        print("✅ OK")
    else:
        print("❌ FAILED")
        print("   Error: Received empty response from API")
        all_passed = False

    print("-" * 50)

    if all_passed:
        print("✅ Model API checks passed!\n")
    else:
        print("❌ Model API check failed. Please fix the issues above.")

    return all_passed
