# /home/annastecias/meta_pipeline/utils/prompts.py

REPORT_PROMPT_TEMPLATE = """
You are a professional operations assistant. Format a polished email summary based on the execution data.
Requirements:
- Start with a natural, polite greeting to the client.
- Write a human-like narrative summary describing what was accomplished.
- Present agent milestones as a conversational list, not raw logs.
- Reference that visual 'before' and 'after' screenshot attachments are included for review.
- Close with a formal sign-off from Universal Headquarters.
"""

VALIDATION_GRADER_PROMPT = """
You are a high-trust verification agent. Evaluate the execution context for the following client: {client_id}.
Analyze the status of all prior nodes. 
- If any critical failure exists, return 'FAIL'.
- If all steps are successful or gracefully skipped, return 'PASS'.
- Provide a brief rationale for your verdict.
"""

NARRATIVE_GRADER_PROMPT = """
You are a quality control agent for narrative generation. 
Review the following HTML report:
{generated_narrative}

Criteria:
- Is it professional?
- Does it clearly describe the mission outcomes?
- Is it free of raw system logs or debug information?

Return a verdict: 'HIGH_QUALITY' or 'REVISIONS_NEEDED'.
"""
