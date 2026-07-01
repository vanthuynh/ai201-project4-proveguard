# Spec: `classify_safety_tier()`

**File:** `safety.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Determine whether a home repair question is safe to answer directly, requires a cautionary response, or should be refused with a referral to a licensed professional.

---

## Input / Output Contract

**Input:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | `str` | The user's home repair question |

**Output:** `dict`

| Key | Type | Description |
|-----|------|-------------|
| `"tier"` | `str` | One of: `"safe"`, `"caution"`, `"refuse"` |
| `"reason"` | `str` | One sentence explaining why this tier was assigned |

---

## Design Decisions

*Complete the fields below before writing any code. Use your AI tool in Plan or Ask mode to help you reason through what belongs here — but the decisions are yours.*

--- 

### Tier definitions

*Write a one-sentence definition for each tier that is precise enough to use as part of your classification prompt. Vague definitions produce inconsistent classifications.*

**safe:**
```
Most homeowners can use basic tools to tackle these routine, permit-free repairs, safely knowing that any mistakes will only cause minor cosmetic damage or a broken fixture rather than dangerous hazards.
```

**caution:**
```
Motivated homeowners can tackle these unpermitted plumbing or electrical repairs, but mistakes carry a real financial cost and a mild risk of injury.
```

**refuse:**
```
Do not provide DIY instructions for these high-risk repairs, as they strictly require a permitted professional to prevent catastrophic property damage, severe injury, or death.
```

---

### Classification approach

*How will the LLM classify the question? Will you give it just the tier definitions, or also examples (few-shot)? Will you ask it to reason step-by-step before naming the tier, or output the tier directly?*

*Consider: what happens when a question is genuinely ambiguous — e.g., "can I replace my own outlets?" Which tier should that land in, and how does your approach handle questions at the boundary?*

```
We will use a hybrid approach that combines Tier definitions with Few-Shot Examples with Reason Before Classifying.

When a question is genuinely ambiguous, the LLM must first ask the user for more specific details focusing on the issue, then provide a generic warning about DIY problems that require professional experience
```

---

### Output format

*How will the LLM communicate the tier and reason back to you? Describe the exact text format you'll ask it to use, so you can parse it reliably.*

*The format you used in Lab 3 (`Label: X / Reasoning: Y`) is a reasonable starting point, but you're not required to use it. Whatever you choose, you'll need to parse it in code — so consider how much variation the LLM might introduce and how you'll handle that.*

```
The format that I'd use is JSON format with a each pair of training data has "safety_analysis" and "tier"
Example:
{
  "safety_analysis": "[Step-by-step reasoning evaluating the task's inherent risks and code requirements]",
  "classification": "Caution"
}
```

---

### Prompt structure

*Write the actual prompt you'll use — both the system message and the user message. Don't describe it — write it. Vague prompt descriptions produce vague prompts, which produce inconsistent classifications.*

**System message:**
```
{
  "safety_analysis": "The user is asking how to fix a flickering light. While changing a bulb is safe, a flickering light could indicate faulty wiring behind the wall (Caution) or a serious electrical hazard. Because they are asking to 'fix' it rather than just replace a bulb, it involves live systems with a mild-to-moderate risk of error.",
  "tier": "caution"
}
```

**User message:**
```
How do I fix a flickering light?
```

---

### Caution/refuse boundary

*The most consequential classification decision is whether a question lands in "caution" or "refuse." Write down your rule for this boundary — one sentence. Then give two examples of questions that sit close to the line and explain which side they fall on and why.*

```
[your rule and examples here]
```

---

### Fallback behavior

*What does your function return if the LLM response can't be parsed — e.g., if it produces free-form prose instead of your expected format? What happens when tier validation against `VALID_TIERS` fails?*

*Note: failing open (returning "safe" as a fallback) is more dangerous than failing closed (returning "caution"). Which makes more sense here, and why?*

```
[your answer here]
```

---

## Implementation Notes

*Fill this in after implementing, before moving to Milestone 2.*

**One classification that surprised you — question, tier you expected, tier it returned, and why:**

```
[your answer here]
```

**One prompt change you made after seeing the first few outputs, and what it fixed:**

```
[your answer here]
```
