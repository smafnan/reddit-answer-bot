"""Topic-aware simulated responses for demo mode (no LLM key configured).

Demo mode is honest: for a few canned topics (laptops/LLMs, Tesla, CS degree) it
returns a realistic grounded answer whose [n] markers point at real mock comments;
for anything else it demonstrates the engine's core behaviour — an honest refusal
rather than a fabricated answer. Every demo report is badged llm_mode="simulated".
"""

import re
from typing import Any, Dict, List, Optional

from schemas import AnswerOutput, QueryPlan

GREETING_RE = re.compile(r"^\s*(hi|hey|hello|yo|thanks|thank you|good (morning|evening))\b", re.IGNORECASE)


def _detect_topic(text: str) -> str:
    t = (text or "").lower()
    if any(w in t for w in ["laptop", "macbook", "rtx", "ollama", "gpu", "vram", "local llm"]):
        return "laptop"
    if any(w in t for w in ["tesla", "model y", "model 3"]) or re.search(r"\b(ev|electric car)\b", t):
        return "tesla"
    if any(w in t for w in ["cs degree", "computer science", "bootcamp", "college degree"]):
        return "cs"
    return "unknown"


def _mock(comment_id, title, sub, author, ups, body, permalink):
    return {
        "comment_id": comment_id,
        "post_title": title,
        "post_url": f"https://www.reddit.com/r/{sub}/comments/{comment_id[3:]}",
        "comment_permalink": permalink,
        "subreddit": sub,
        "author": author,
        "ups": ups,
        "body": body,
        "created_utc": 1718112000.0,
    }


def get_mock_retrieved_comments(query: str) -> List[Dict[str, Any]]:
    """Realistic mock Reddit comments keyed to the query topic (demo mode only)."""
    topic = _detect_topic(query)
    if topic == "laptop":
        return [
            _mock("t1_lap001", "MacBook Pro M3 Max vs RTX 4090 laptop for local LLMs", "LocalLLaMA", "llm_dev_99", 142,
                  "I've run models on both. Unified Memory on macOS is a game-changer for inference — a 128GB MacBook Pro can run Llama 3 70B, whereas the mobile RTX 4090 only has 16GB VRAM so you're capped at ~8B models. But for heavy CUDA training NVIDIA is mandatory.",
                  "https://www.reddit.com/r/LocalLLaMA/comments/lap001/_/clap001/"),
            _mock("t1_lap002", "MacBook Pro M3 Max vs RTX 4090 laptop for local LLMs", "LocalLLaMA", "cuda_coder", 89,
                  "Don't buy a laptop for heavy training — they thermal throttle in minutes. Get a mid-range RTX 4060 laptop to write code and spend the rest on cloud GPUs (RunPod, Paperspace). Renting an A100 is far cheaper than a $4,000 laptop.",
                  "https://www.reddit.com/r/LocalLLaMA/comments/lap001/_/clap002/"),
            _mock("t1_lap003", "Best laptop for machine learning in college?", "LearnMachineLearning", "grad_student_ml", 56,
                  "As a student get an RTX 4060/4070 Windows laptop — you need CUDA for assignments and Apple's MPS is a pain with some PyTorch libs. Note the laptop 4090 is NOT a desktop 4090: ~40% slower and 16GB vs 24GB VRAM.",
                  "https://www.reddit.com/r/LearnMachineLearning/comments/lap003/_/clap003/"),
        ]
    if topic == "tesla":
        return [
            _mock("t1_tes001", "Is a Tesla Model Y worth it in 2026?", "teslamotors", "ev_pioneer", 210,
                  "Model Y owner for 2 years. The Supercharger network is the #1 reason to buy a Tesla over another EV — plug-and-play and reliable, and OTA updates keep adding features. Build quality is hit or miss though; I had panel alignment issues at delivery.",
                  "https://www.reddit.com/r/teslamotors/comments/tes001/_/ctes001/"),
            _mock("t1_tes002", "Is a Tesla Model Y worth it in 2026?", "teslamotors", "mech_guy", 115,
                  "Mechanic's view: Tesla restricts parts to independent shops, which drives up repair times and insurance costs. They also depreciate fast because Tesla keeps cutting new-car prices, killing resale on older models.",
                  "https://www.reddit.com/r/teslamotors/comments/tes001/_/ctes002/"),
            _mock("t1_tes003", "Model Y long-term ownership — regrets?", "electricvehicles", "daily_driver_ev", 74,
                  "Zero regrets on the drivetrain and charging, but the ride is stiff and road noise is real. If you want comfort look elsewhere; if you want tech and a charging network, the Model Y is hard to beat.",
                  "https://www.reddit.com/r/electricvehicles/comments/tes003/_/ctes003/"),
        ]
    if topic == "cs":
        return [
            _mock("t1_cs001", "Is a CS degree still worth it?", "cscareerquestions", "hiring_manager_swe", 320,
                  "A CS degree is worth it. It gets you past HR auto-filters that reject bootcamp grads, and it teaches data structures, OS, compilers and databases that matter for long-term growth. Bootcamps mostly teach you to wire up React.",
                  "https://www.reddit.com/r/cscareerquestions/comments/cs001/_/ccs001/"),
            _mock("t1_cs002", "Is a CS degree still worth it?", "cscareerquestions", "bootcamp_survivor", 182,
                  "Degrees are overpriced and often teach outdated tech. A strong portfolio, open-source work and networking can land a job without 4 years of debt — I did it. Depends on your discipline and market.",
                  "https://www.reddit.com/r/cscareerquestions/comments/cs001/_/ccs002/"),
            _mock("t1_cs003", "Regretting my CS degree?", "csMajors", "new_grad_2026", 96,
                  "The 2025-26 entry market is brutal regardless of path. A degree helps but isn't enough alone — internships and projects are what actually got my classmates hired.",
                  "https://www.reddit.com/r/csMajors/comments/cs003/_/ccs003/"),
        ]
    # Unknown topic → a single thin comment, so the coverage gate refuses honestly.
    return [
        _mock("t1_gen001", "General discussion thread", "AskReddit", "community_voice", 42,
              "This has pros and cons — some people love it, others warn about the cost. Check reviews before deciding.",
              "https://www.reddit.com/r/AskReddit/comments/gen001/_/cgen001/"),
    ]


def _conversation_slice(prompt: str) -> str:
    """The real conversation (history + current message), excluding the few-shot
    examples in the system prompt, so demo topic detection isn't contaminated."""
    idx = prompt.find("Conversation so far:")
    return prompt[idx:] if idx != -1 else _last_user_line(prompt)


def get_simulated_plan(prompt: str) -> Dict[str, Any]:
    """Build a QueryPlan for demo mode from the understand prompt text."""
    # The current user message is embedded in the prompt; detect greeting/topic.
    if GREETING_RE.search(_last_user_line(prompt)):
        return QueryPlan(
            intent="greeting",
            direct_reply="Hey! Ask me anything and I'll answer from real Reddit discussions — "
            "product advice, how-tos, comparisons, opinions. What do you want to know?",
        ).model_dump()

    topic = _detect_topic(_conversation_slice(prompt))
    q = _last_user_line(prompt) or "the question"
    if topic == "laptop":
        return QueryPlan(intent="answerable", standalone_question=q or "Best laptop for local LLMs?",
                         search_queries=["best laptop local llm", "macbook vs rtx laptop llm", "laptop vram for llama"],
                         subreddits=["LocalLLaMA", "LearnMachineLearning"], recency_sensitive=True).model_dump()
    if topic == "tesla":
        return QueryPlan(intent="answerable", standalone_question=q or "Is a Tesla Model Y worth it?",
                         search_queries=["tesla model y worth it", "tesla model y regret", "tesla build quality"],
                         subreddits=["teslamotors", "electricvehicles"], recency_sensitive=True).model_dump()
    if topic == "cs":
        return QueryPlan(intent="answerable", standalone_question=q or "Is a CS degree worth it?",
                         search_queries=["cs degree worth it", "cs degree vs bootcamp", "regret cs degree"],
                         subreddits=["cscareerquestions", "csMajors"], recency_sensitive=False).model_dump()
    # Unknown but answerable: still plan, so retrieval->gate demonstrates refusal.
    return QueryPlan(intent="answerable", standalone_question=q,
                     search_queries=[q], subreddits=[], recency_sensitive=False).model_dump()


def get_simulated_answer(prompt: str) -> Dict[str, Any]:
    """Build an AnswerOutput for demo mode from the answer prompt (numbered pack)."""
    topic = _detect_topic(prompt)
    if topic == "laptop":
        return AnswerOutput(
            tldr="For running large local models a high-RAM MacBook wins; for CUDA training or budget, an NVIDIA laptop (or cloud GPUs) is better [1][2].",
            answer_markdown=(
                "For **local LLM inference**, a MacBook Pro with lots of Unified Memory can load far bigger models "
                "(e.g. Llama 3 70B on 128GB) than an NVIDIA laptop, whose mobile RTX 4090 is capped at 16GB VRAM [1]. "
                "But for **heavy training or CUDA work**, NVIDIA is effectively mandatory, and many people suggest a "
                "cheaper laptop plus rented cloud GPUs rather than a $4,000 machine [2]. Students note the laptop 4090 "
                "is ~40% slower than the desktop card and Apple's MPS can be fiddly with some PyTorch libraries [3]."
            ),
            used_citation_indices=[1, 2, 3], grounded=True,
            suggested_followups=["What about a desktop instead?", "How much VRAM for a 13B model?"],
        ).model_dump()
    if topic == "tesla":
        return AnswerOutput(
            tldr="Owners love the Supercharger network and software but warn about build quality, fast depreciation, and repair costs [1][2].",
            answer_markdown=(
                "Reddit owners are broadly positive on the **charging and software**: the Supercharger network is the "
                "top reason people pick a Tesla over other EVs, and OTA updates keep adding features [1]. The common "
                "**warnings** are inconsistent build quality, a stiff ride, fast depreciation from Tesla's price cuts, "
                "and pricier repairs/insurance because parts are restricted [2][3]. Net: great tech and charging, "
                "weaker on comfort and long-term resale."
            ),
            used_citation_indices=[1, 2, 3], grounded=True,
            suggested_followups=["How does it compare to a Hyundai Ioniq 5?", "Is used or new the better deal?"],
        ).model_dump()
    if topic == "cs":
        return AnswerOutput(
            tldr="Most say a CS degree still helps (HR filters, fundamentals) but isn't enough alone in the 2026 market — projects and internships matter [1][3].",
            answer_markdown=(
                "The common view is that a CS degree **still helps**: it clears HR auto-filters and teaches "
                "fundamentals (data structures, OS, databases) that pay off long-term [1]. The **counterpoint** is that "
                "degrees are expensive and sometimes outdated, and a strong portfolio plus networking can land a job "
                "without the debt [2]. Recent grads stress that in the tough 2025-26 market a degree **isn't enough by "
                "itself** — internships and real projects are what actually get people hired [3]."
            ),
            used_citation_indices=[1, 2, 3], grounded=True,
            suggested_followups=["Is a bootcamp worth it instead?", "Which projects impress recruiters?"],
        ).model_dump()
    # Unknown topic shouldn't normally reach here (the gate refuses first), but be safe.
    return AnswerOutput(
        answer_markdown="Reddit doesn't clearly cover this in demo mode.",
        grounded=False,
        refusal_reason="Reddit doesn't clearly cover this in demo mode. Add an API key and Reddit credentials for real answers.",
    ).model_dump()


def _last_user_line(prompt: str) -> str:
    """Pull the most likely 'current user message' out of a prompt for topic/greeting detection."""
    m = re.search(r"Current user message:\s*'?\"?(.+?)'?\"?\s*$", prompt, re.MULTILINE)
    if m:
        return m.group(1).strip()
    m = re.search(r"Question:\s*(.+)", prompt)
    if m:
        return m.group(1).strip()
    return prompt[-200:]


def get_simulated_response(prompt: str, response_schema: Optional[Any]) -> Dict[str, Any]:
    """Dispatch demo-mode fallback by schema (QueryPlan / AnswerOutput)."""
    if response_schema is QueryPlan:
        return get_simulated_plan(prompt)
    if response_schema is AnswerOutput:
        return get_simulated_answer(prompt)
    return {}
