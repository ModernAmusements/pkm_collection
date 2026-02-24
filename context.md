The workflow should begin by cropping the screenshot. After that, the image must be converted to grayscale, sharpened, and divided into predefined zones. Each zone is then scaled appropriately to optimize data extraction from the Pokémon cards.

The same process applies to Trainer cards.

For Pokémon cards, Zone 1 and Zone 4 are critical for extraction.
For Trainer cards, Zone 2, Zone 4, and Zone 5 are essential.

The API should only be used if OCR fails or does not provide sufficient information about the Pokémon. In that case, the API is used to retrieve the remaining missing data.

Important: Zone 4 on Pokémon cards contains the card number specific to the TCG Pocket sets. These numbers do not match the general Pokémon API numbering, so relying on the API for this field leads to incorrect results.

## Pyhton 

AI Ruleset for Writing Python Code

1. Core Principles
	•	Write clear, readable, and maintainable code.
	•	Prefer simplicity over cleverness.
	•	Follow PEP 8 and Pythonic conventions.
	•	Avoid unnecessary abstractions.
	•	Always reason before implementing.

⸻

2. Structure & Organization
	•	Use meaningful module and file names.
	•	Keep functions small and focused on one responsibility.
	•	Avoid global state.
	•	Use if __name__ == "__main__": for execution entry points.
	•	Group related logic into classes only when state management is required.

⸻

3. Naming Conventions
	•	snake_case → variables and functions
	•	PascalCase → classes
	•	UPPER_CASE → constants
	•	Avoid unclear abbreviations.
	•	Use descriptive names that reflect intent.

⸻

4. Typing & Documentation
	•	Always use type hints.
	•	Add docstrings to all public functions and classes.
	•	Use Google-style or NumPy-style docstrings consistently.
	•	Document side effects and edge cases.

Example:

def extract_card_data(image_path: str) -> dict:
    """
    Extract structured card data from an image.

    Args:
        image_path: Path to the card image.

    Returns:
        Dictionary containing extracted card attributes.
    """


⸻

5. Error Handling
	•	Never silently ignore exceptions.
	•	Catch specific exceptions only.
	•	Use custom exceptions for domain-specific logic.
	•	Log meaningful error messages.

⸻

6. Performance & Efficiency
	•	Avoid premature optimization.
	•	Use list comprehensions where readable.
	•	Prefer built-in functions over manual loops.
	•	Use generators for large datasets.

⸻

7. Security Rules
	•	Never use eval() or exec() unless absolutely necessary.
	•	Sanitize external input.
	•	Do not hardcode secrets.
	•	Validate file paths and user input.

⸻

8. Testing Requirements
	•	Write unit tests for all core logic.
	•	Test edge cases and invalid input.
	•	Keep business logic independent from I/O for testability.
	•	Use fixtures for repeated setup.

⸻

9. Logging & Debugging
	•	Use the logging module instead of print().
	•	Separate debug logs from production logs.
	•	Never expose sensitive information in logs.

⸻

10. Code Quality Checks

Before finalizing code, verify:
	•	Is the logic correct and edge-case safe?
	•	Is the code readable without comments explaining obvious behavior?
	•	Are types correct and consistent?
	•	Are exceptions handled properly?
	•	Is the solution minimal and maintainable?

⸻

11. AI-Specific Constraints
	•	Do not hallucinate libraries or APIs.
	•	Only use stable, well-known dependencies unless specified.
	•	If assumptions are required, state them clearly.
	•	Prefer deterministic solutions over probabilistic ones.

⸻

If needed, I can refine this into a strict enforceable checklist or adapt it for a specific domain (e.g., OCR pipelines, ML systems, API services, macOS apps).

## Testing 

For testing, use the images in the screenshots/test folder and display the defined zones in the docs folder

