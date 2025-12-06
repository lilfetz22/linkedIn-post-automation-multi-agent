Here is the task description based on the screenshot, formatted for an AI coding agent.

***

**Task: Fix fragile error handling in `agents/image_prompt_agent.py`**

**Context:**
In `agents/image_prompt_agent.py` (around line 196), the code currently checks for a specific error using broad string matching: `if "final_post" in error_msg`.

This logic is fragile because it generates false positives. If an unrelated error message merely mentions the variable name "final_post" (e.g., "LLM failed processing final_post data"), it is incorrectly treated as an input validation error and bypasses the fallback logic.

**Instructions:**
1.  Locate the error handling block around line 196.
2.  Refactor the condition to be more specific. Instead of checking for a substring in a generic error message, check the exception type and the specific validation error message.
3.  Ensure `ValidationError` is imported (likely from Pydantic or the relevant library).
4.  Update the condition to verify that the exception `e` is an instance of `ValidationError` AND that the string `"Missing 'final_post'"` is present in the exception message.

**Suggested Implementation:**
Replace the current `if` check with:

```python
from pydantic import ValidationError # Ensure this is imported at the top

# ... inside the error handler ...

# Check specifically for validation errors regarding missing 'final_post'
if isinstance(e, ValidationError) and "Missing 'final_post'" in str(e):
    # Handle input validation error logic here
    pass 
```