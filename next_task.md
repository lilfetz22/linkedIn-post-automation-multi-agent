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

***

**Task: Refactor magic number in truncation logic in `agents/writer_agent.py`**

**Context:**
In `agents/writer_agent.py` (lines 185-187), the code currently uses a "magic number" (`120`) when calculating the character limit for the fallback post. This number is intended as a buffer for the appended sign-off string (`"\n\n- Tech Audience Accelerator"`), but `120` is excessive (the string is only ~30 chars) and lacks semantic meaning.

**Instructions:**
1.  Locate the truncation logic around lines 185-187.
2.  Replace the hardcoded value `120` with a named constant `SIGNOFF_BUFFER`.
3.  Set the `SIGNOFF_BUFFER` value to `50` (a safer, more reasonable buffer size).
4.  Update both the `if` condition and the slice operation to use this new constant.
5.  Add a comment explaining that this buffer reserves space for the sign-off.

**Suggested Implementation:**
```python
SIGNOFF_BUFFER = 50  # Buffer for sign-off text (~30 chars)

if count_chars(fallback_post) >= MAX_CHARS - SIGNOFF_BUFFER:
    trimmed = fallback_post[: MAX_CHARS - SIGNOFF_BUFFER]
    fallback_post = f"{trimmed}\n\n- Tech Audience Accelerator"
```