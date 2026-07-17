"""Prompts for conversation summarization and memory extraction."""

MEMORY_EXTRACTION_PROMPT = """You are an expert memory extraction assistant.

Analyze the conversation and return ONLY valid JSON.

Tasks:
1. Generate a conversation title (max 6 words).
2. Generate a short summary (max 3 sentences).
3. Extract semantic memories.
4. Extract episodic memories.

Rules for Memories:
- Extract at most 10 semantic memories.
- Extract at most 10 episodic memories.
- Only extract memories that would still be useful weeks or months later.
- If nothing is worth remembering, return empty arrays for semantic_memories and episodic_memories.
- Ignore greetings, filler, temporary questions, and generic knowledge.
- Do not duplicate existing memories.
- Use the importance scale:
  1.0 = critical identity
  0.9 = strong preference
  0.8 = important project fact
  0.6 = significant event
  0.3 = minor
  <=0.1 = ignore

Return exactly this JSON schema:
{{
  "title": "...",
  "summary": "...",
  "semantic_memories": [
    {{
      "type": "...",
      "category": "...",
      "text": "...",
      "importance": 0.0,
      "tags": []
    }}
  ],
  "episodic_memories": [
    {{
      "type": "...",
      "summary": "...",
      "importance": 0.0,
      "tags": []
    }}
  ]
}}

Conversation:
{conversation}
"""
