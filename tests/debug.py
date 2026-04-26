# # Run this as a standalone script — save as debug_speed.py in project root

# import time
# import os
# from openai import OpenAI
# from dotenv import load_dotenv

# load_dotenv()

# client = OpenAI(
#     base_url=os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"),
#     api_key="lm-studio",
# )

# MODEL = os.getenv("LM_STUDIO_MODEL", "qwen3.5")

# # Minimal prompt — strips everything to bare bones
# start = time.time()
# response = client.chat.completions.create(
#     model=MODEL,
#     messages=[
#         {
#             "role": "user",
#             "content": "Reply with just this JSON and nothing else: {\"test\": \"ok\"}"
#         }
#     ],
#     max_tokens=50,
# )
# elapsed = time.time() - start

# raw = response.choices[0].message.content
# print(f"Time:     {elapsed:.1f}s")
# print(f"Raw response:")
# print(raw[:500])  # first 500 chars — will show <think> tags if thinking is on
# print(f"\nTotal tokens: {response.usage.total_tokens if response.usage else 'unknown'}")

# Save as debug_instructor.py in project root
# ###### Test 2##########
# import time
# import os
# import instructor
# from openai import OpenAI
# from pydantic import BaseModel
# from dotenv import load_dotenv

# load_dotenv()

# client = instructor.from_openai(
#     OpenAI(
#         base_url=os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"),
#         api_key="lm-studio",
#     ),
#     mode=instructor.Mode.JSON_SCHEMA,
# )

# MODEL = os.getenv("LM_STUDIO_MODEL", "qwen3.5")

# # Test 1 — tiny schema, see if instructor itself adds overhead
# class Tiny(BaseModel):
#     result: str
#     confidence: int

# start = time.time()
# response = client.chat.completions.create(
#     model=MODEL,
#     response_model=Tiny,
#     max_retries=1,
#     messages=[{"role": "user", "content": "Reply with result='ok' and confidence=3"}],
# )
# t1 = time.time() - start
# print(f"Test 1 — tiny schema:     {t1:.1f}s → {response}")

# # Test 2 — same tiny schema, check if size matters
# from enum import Enum
# class Pace(str, Enum):
#     SLOW = "slow_burn"
#     FAST = "frenetic"

# class Medium(BaseModel):
#     title: str
#     pacing: Pace
#     score: int

# start = time.time()
# response = client.chat.completions.create(
#     model=MODEL,
#     response_model=Medium,
#     max_retries=1,
#     messages=[{"role": "user", "content": "Film: Parasite. Reply with title, pacing (slow_burn or frenetic), score 1-5"}],
# )
# t2 = time.time() - start
# print(f"Test 2 — medium schema:   {t2:.1f}s → {response}")

# print()
# print(f"Bare request baseline:    ~1.3s")
# print(f"Instructor tiny schema:   {t1:.1f}s")
# print(f"Instructor medium schema: {t2:.1f}s")
# print()
# if t1 < 5:
#     print("✅ Instructor overhead is minimal — bottleneck is prompt size or schema complexity")
# else:
#     print("🔴 Instructor itself is adding significant overhead")

# Save as debug_prompt.py in project root
# import os
# from dotenv import load_dotenv
# from src.enrichment.store import load_enriched
# from src.annotation.annotator import _build_prompt

# load_dotenv()

# records = load_enriched()
# r = next(x for x in records if x.title == 'Parasite')

# prompt = _build_prompt(r)
# # Rough token estimate: 1 token ≈ 4 chars
# char_count  = len(prompt)
# token_est   = char_count // 4
# schema_size = len(str(r.model_dump()))

# print(f"Prompt characters:     {char_count}")
# print(f"Prompt tokens (est):   {token_est}")
# print(f"Schema JSON size:      {schema_size} chars")
# print()
# print("--- PROMPT ---")
# print(prompt)

# Save as debug_schema_size.py
from src.annotation.schema import CraftAnnotation
import json

schema = CraftAnnotation.model_json_schema()
schema_str = json.dumps(schema, indent=2)
print(f"Schema characters: {len(schema_str)}")
print(f"Schema tokens est: {len(schema_str) // 4}")
print()
print(schema_str[:2000])