"""Topic-aware simulated responses for demo mode (no API key configured).

Simulated data is clearly labelled: fact-check entries produced here carry a
"[Demo sample]" marker and unmatched claims are reported as *Unverified* —
demo mode never fabricates a "Verified" verdict for a claim it didn't check.
The final report also carries ``llm_mode: "simulated"`` so the UI can badge it.
"""

import re
from typing import Any, Dict, List, Optional

from schemas import (
    BatchCommentEvaluation,
    FactCheckClaim,
    FactCheckOutput,
    IntelligenceReport,
    KnowledgeGraphOutput,
    PerspectiveAndContradictionOutput,
    QueryExpansionOutput,
)

DEMO_NOTE = "[Demo sample] No live verification was performed — connect an API key for real analysis. "


def _detect_topic(prompt: str) -> Dict[str, bool]:
    query_match = re.search(r'query:?\s*"([^"]+)"|regarding:?\s*"([^"]+)"|about:?\s*"([^"]+)"', prompt)
    query_text = ""
    if query_match:
        query_text = query_match.group(1) or query_match.group(2) or query_match.group(3) or ""
    if not query_text:
        query_text = prompt
    q = query_text.lower()
    return {
        "laptop": any(w in q for w in ["laptop", "macbook", "rtx", "ollama", "gpu", "vram"]),
        "tesla": any(w in q for w in ["tesla", "model y", "model 3"]) or bool(re.search(r"\b(ev|car|electric)\b", q)),
        "cs": any(w in q for w in ["cs degree", "computer science", "career", "college", "degree", "university"]),
    }


def get_mock_retrieved_comments(query: str) -> List[Dict[str, Any]]:
    """Realistic mock Reddit comments keyed to the query topic."""
    topic = _detect_topic(f'query: "{query}"')
    if topic["laptop"]:
        return [
            {
                "post_title": "MacBook Pro M3 Max vs RTX 4090 laptop for local LLMs",
                "post_url": "https://reddit.com/r/LocalLLaMA/comments/123456",
                "subreddit": "LocalLLaMA",
                "author": "llm_dev_99",
                "ups": 142,
                "body": "I've trained ML models on both systems. Unified Memory on macOS is a game-changer for inference. A MacBook Pro with 128GB of Unified Memory can run Llama 3 70B at decent token-per-second speeds, whereas the mobile RTX 4090 only has 16GB VRAM, limiting you to 8B models. However, if you write custom CUDA kernels or do heavy PyTorch training, NVIDIA is mandatory.",
                "depth": 0,
                "created_utc": 1718112000,
            },
            {
                "post_title": "MacBook Pro M3 Max vs RTX 4090 laptop for local LLMs",
                "post_url": "https://reddit.com/r/LocalLLaMA/comments/123456",
                "subreddit": "LocalLLaMA",
                "author": "cuda_coder",
                "ups": 89,
                "body": "Don't buy a laptop for heavy training; they thermal throttle in minutes and run like jets. Buy a mid-range laptop (RTX 4060) to write code, and spend the remaining $2,000 on RunPod or Paperspace. Renting an A100 is way cheaper than buying a $4,000 laptop.",
                "depth": 1,
                "created_utc": 1718115600,
            },
            {
                "post_title": "Best laptop for machine learning in college?",
                "post_url": "https://reddit.com/r/LearnMachineLearning/comments/789101",
                "subreddit": "LearnMachineLearning",
                "author": "grad_student_ml",
                "ups": 56,
                "body": "If you're a student, get an RTX 4060 or 4070 Windows laptop. You need CUDA for school assignments, and Apple's MPS is sometimes a pain to configure with PyTorch libraries. Also, laptop RTX 4090 is NOT a desktop 4090, it's 40% slower and has only 16GB VRAM compared to 24GB desktop.",
                "depth": 0,
                "created_utc": 1718120000,
            },
        ]
    if topic["tesla"]:
        return [
            {
                "post_title": "Is a Tesla Model Y worth it in 2024?",
                "post_url": "https://reddit.com/r/teslamotors/comments/111222",
                "subreddit": "teslamotors",
                "author": "ev_pioneer",
                "ups": 210,
                "body": "Model Y owner for 2 years here. The Supercharger network is the primary reason to buy a Tesla over any other EV. It's plug-and-play and incredibly reliable. The OTA software updates are great too. However, build quality is still a hit or miss—I had panel alignment issues at delivery and the cabin has some rattles.",
                "depth": 0,
                "created_utc": 1718112000,
            },
            {
                "post_title": "Is a Tesla Model Y worth it in 2024?",
                "post_url": "https://reddit.com/r/teslamotors/comments/111222",
                "subreddit": "teslamotors",
                "author": "mech_guy",
                "ups": 115,
                "body": "Mechanic's perspective: Tesla restricts replacement parts to independent shops, which drives up repair times and insurance costs. Also, they depreciate incredibly fast because Tesla frequently cuts prices on new cars, killing the resale value of older models.",
                "depth": 1,
                "created_utc": 1718116000,
            },
        ]
    if topic["cs"]:
        return [
            {
                "post_title": "Is a CS degree useless now?",
                "post_url": "https://reddit.com/r/cscareerquestions/comments/333444",
                "subreddit": "cscareerquestions",
                "author": "hiring_manager_swe",
                "ups": 320,
                "body": "A CS degree is absolutely worth it. It gets you past HR screening algorithms that instantly auto-reject bootcamp grads. It also teaches data structures, low-level OS, compilers, and database internals, which are crucial for long-term career growth. Bootcamps only teach you how to write simple React components.",
                "depth": 0,
                "created_utc": 1718112000,
            },
            {
                "post_title": "Is a CS degree useless now?",
                "post_url": "https://reddit.com/r/cscareerquestions/comments/333444",
                "subreddit": "cscareerquestions",
                "author": "bootcamp_survivor",
                "ups": 182,
                "body": "Degrees are overpriced. A good portfolio, open source contributions, and solid networking can land you a job without 4 years of debt. Many universities teach outdated tech and languages no one uses in modern web dev.",
                "depth": 1,
                "created_utc": 1718115000,
            },
        ]
    return [
        {
            "post_title": "General Discussion Thread",
            "post_url": "https://reddit.com/r/askreddit/comments/555666",
            "subreddit": "askreddit",
            "author": "community_voice",
            "ups": 42,
            "body": "This topic has several pros and cons. Some users recommend investing in it for long-term value, while others prefer cheaper alternatives or warn of potential pitfalls. Make sure to check reviews and compatibility before deciding.",
            "depth": 0,
            "created_utc": 1718112000,
        }
    ]


def get_simulated_claims(query: str) -> List[str]:
    topic = _detect_topic(f'query: "{query}"')
    if topic["laptop"]:
        return [
            "Unified Memory on MacBook is shared between CPU and GPU, making large LLMs run locally.",
            "The laptop version of the NVIDIA RTX 4090 performs identically to the desktop RTX 4090.",
        ]
    if topic["tesla"]:
        return [
            "Tesla Model Y was the best-selling car globally in 2023.",
            "Tesla's Full Self-Driving (FSD) is a Level 5 fully autonomous system.",
        ]
    return ["Over 70% of professional software developers have a college degree."]


def get_simulated_response(prompt: str, response_schema: Optional[Any]) -> Dict[str, Any]:
    """Returns a schema-shaped dict of topic-aware demo data."""
    topic = _detect_topic(prompt)

    if response_schema is QueryExpansionOutput:
        if topic["laptop"]:
            queries = [
                "best ai laptop for machine learning local training",
                "running ollama deepseek coder on laptop performance",
                "rtx 4090 vs macbook m3 max for local llms",
                "budget laptop for AI engineering students",
                "cuda programming on windows laptop requirements",
                "laptop vs cloud for training pytorch models",
                "how much vram do i need for llama 3 8b",
                "common mistakes when buying laptop for deep learning",
            ]
        elif topic["tesla"]:
            queries = [
                "should I buy a tesla model y pros and cons",
                "tesla model 3 long term reliability issues",
                "electric vehicle vs gas car cost comparison reddit",
                "buying used tesla model s model x common mistakes",
                "tesla insurance cost and real experiences",
                "tesla build quality panel gaps hardware issues",
                "what do mechanics think of tesla repairs",
            ]
        elif topic["cs"]:
            queries = [
                "is a cs degree worth it in 2026 tech market",
                "self taught software engineer vs cs degree jobs",
                "computer science degree vs bootcamp career path",
                "cost of cs degree vs entry level starting salary",
                "does university prestige matter for software engineering",
                "regretting my computer science degree career change",
            ]
        else:
            queries = [
                "reddit opinions and discussions on this topic",
                "what do professionals say about this",
                "common problems and issues with this",
                "is it worth the price and cost",
                "alternatives and comparisons to this",
                "beginner guides and tutorials for this",
            ]
        return {"queries": queries}

    if response_schema is BatchCommentEvaluation:
        evals = []
        for idx in range(25):
            spam = idx % 6 == 0
            evals.append(
                {
                    "index": idx,
                    "is_spam_or_low_effort": spam,
                    "quality_score": round(0.15 if spam else 0.85 - (idx * 0.02), 2),
                    "reason": "Low effort comment/joke." if spam else "Detailed hardware benchmarks and user experience.",
                }
            )
        return {"evaluations": evals}

    if response_schema is PerspectiveAndContradictionOutput:
        if topic["laptop"]:
            perspectives = [
                {
                    "name": "Local LLM Enthusiasts",
                    "consensus": "Unified Memory on macOS is superior for running huge models locally.",
                    "supporting_points": [
                        "MacBook Pro with 64GB/128GB of Unified Memory can run large 70B models.",
                        "Standard laptops with NVIDIA mobile GPUs are capped at 16GB VRAM, restricting them to smaller 8B models.",
                    ],
                },
                {
                    "name": "ML Researchers & CUDA Engineers",
                    "consensus": "NVIDIA Windows/Linux hardware is mandatory for active training.",
                    "supporting_points": [
                        "PyTorch and TensorFlow have primary, native acceleration on CUDA.",
                        "Mac's Metal (MPS) is catching up but still lacks compatibility for many low-level libraries.",
                    ],
                },
                {
                    "name": "Cost-Conscious Students",
                    "consensus": "Rent cloud GPUs instead of buying a high-end AI laptop.",
                    "supporting_points": [
                        "Buy a mid-range laptop (e.g. RTX 4060) and use remaining budget on RunPod or Google Colab.",
                        "Renting a desktop RTX 4090 or A100 is far more cost-effective for short projects.",
                    ],
                },
            ]
            contradictions = [
                "Unified Memory vs. Dedicated CUDA: macOS is better for local inference of large models, but NVIDIA is required for writing CUDA code and model training.",
                "High-end Laptop vs. Thin Client + Cloud: Some users insist on having a local GPU, while others argue that laptop thermal limits make cloud training superior.",
            ]
        elif topic["tesla"]:
            perspectives = [
                {
                    "name": "Long-Term Tesla Owners",
                    "consensus": "Supercharger network and software updates make ownership incredibly convenient.",
                    "supporting_points": [
                        "Charging infrastructure is miles ahead of CCS standard competitors.",
                        "Over-the-air updates continuously add features and improve efficiency.",
                    ],
                },
                {
                    "name": "Automotive Mechanics & DIYers",
                    "consensus": "Build quality is inconsistent and repairs are expensive and heavily restricted.",
                    "supporting_points": [
                        "Frequent complaints about panel gaps, paint quality, and interior rattles.",
                        "Tesla restricts parts distribution, making independent repairs difficult.",
                    ],
                },
            ]
            contradictions = [
                "Build quality vs. Tech stack: Enthusiasts praise the software, infotainment, and autopilot, while traditional drivers complain about subpar cabin materials and mechanical quality control."
            ]
        elif topic["cs"]:
            perspectives = [
                {
                    "name": "Senior Software Engineers & Managers",
                    "consensus": "A degree teaches foundational theory (algorithms, systems) that bootcamps ignore.",
                    "supporting_points": [
                        "Helps pass resumes through automated HR screening filters.",
                        "Teaches low-level systems, networking, and data structures crucial for long-term career growth.",
                    ],
                },
                {
                    "name": "Bootcamp Grads & Self-Taught Developers",
                    "consensus": "Degrees are overly expensive and teach outdated technologies.",
                    "supporting_points": [
                        "A good portfolio and practical web/app dev skills can land jobs without 4 years of debt.",
                        "College programs rarely teach modern web frameworks, git workflow, or CI/CD.",
                    ],
                },
            ]
            contradictions = [
                "Foundational theory vs. Practical tools: Degree advocates focus on deep CS topics, while self-taught advocates argue that practical, modern building skills are what get you hired in startups."
            ]
        else:
            perspectives = [
                {
                    "name": "Experienced Professionals",
                    "consensus": "This solution has clear benefits for production use-cases.",
                    "supporting_points": ["Provides scalability and support.", "Integrates well with existing standards."],
                },
                {
                    "name": "Hobbyists and Beginners",
                    "consensus": "The learning curve is steep and costs might not be justified.",
                    "supporting_points": [
                        "Hard to configure without background knowledge.",
                        "Free or open-source alternatives are often sufficient for smaller projects.",
                    ],
                },
            ]
            contradictions = [
                "Complexity vs. Scalability: Debates center on whether the complex setup is worth the long-term maintainability benefits."
            ]
        return {"perspectives": perspectives, "contradictions": contradictions}

    if response_schema is KnowledgeGraphOutput:
        if topic["laptop"]:
            nodes = [
                {"id": "macbook-pro", "label": "MacBook Pro", "type": "Hardware"},
                {"id": "nvidia-rtx", "label": "NVIDIA RTX Mobile", "type": "Hardware"},
                {"id": "unified-memory", "label": "Unified Memory", "type": "Concept"},
                {"id": "vram", "label": "VRAM", "type": "Concept"},
                {"id": "ollama", "label": "Ollama", "type": "Software"},
                {"id": "cuda", "label": "CUDA", "type": "Software"},
                {"id": "pytorch", "label": "PyTorch", "type": "Software"},
                {"id": "runpod", "label": "RunPod (Cloud)", "type": "Organization"},
            ]
            edges = [
                {"source": "macbook-pro", "target": "unified-memory", "label": "features"},
                {"source": "unified-memory", "target": "ollama", "label": "allows running 70B models on"},
                {"source": "nvidia-rtx", "target": "vram", "label": "limited to 16GB"},
                {"source": "nvidia-rtx", "target": "cuda", "label": "supports"},
                {"source": "cuda", "target": "pytorch", "label": "accelerates"},
                {"source": "runpod", "target": "nvidia-rtx", "label": "rents high-end"},
            ]
        elif topic["tesla"]:
            nodes = [
                {"id": "tesla", "label": "Tesla Inc.", "type": "Organization"},
                {"id": "model-y", "label": "Model Y", "type": "Hardware"},
                {"id": "supercharger", "label": "Supercharger Network", "type": "Hardware"},
                {"id": "ev-tax-credit", "label": "EV Tax Credit", "type": "Concept"},
                {"id": "ccs-adapter", "label": "CCS Adapter", "type": "Hardware"},
                {"id": "depreciation", "label": "High Depreciation", "type": "Concept"},
            ]
            edges = [
                {"source": "tesla", "target": "model-y", "label": "manufactures"},
                {"source": "tesla", "target": "supercharger", "label": "operates"},
                {"source": "model-y", "target": "ev-tax-credit", "label": "qualifies for"},
                {"source": "model-y", "target": "depreciation", "label": "suffers from"},
                {"source": "supercharger", "target": "ccs-adapter", "label": "compatible via"},
            ]
        elif topic["cs"]:
            nodes = [
                {"id": "cs-degree", "label": "Computer Science Degree", "type": "Concept"},
                {"id": "bootcamp", "label": "Coding Bootcamp", "type": "Concept"},
                {"id": "algorithms", "label": "Data Structures & Algorithms", "type": "Concept"},
                {"id": "hr-screening", "label": "HR Automated Filters", "type": "Concept"},
                {"id": "portfolio", "label": "GitHub Portfolio", "type": "Software"},
            ]
            edges = [
                {"source": "cs-degree", "target": "algorithms", "label": "teaches deeply"},
                {"source": "cs-degree", "target": "hr-screening", "label": "bypasses"},
                {"source": "bootcamp", "target": "portfolio", "label": "focuses on building"},
                {"source": "portfolio", "target": "hr-screening", "label": "struggles to bypass alone"},
            ]
        else:
            nodes = [
                {"id": "core-topic", "label": "Core Subject", "type": "Concept"},
                {"id": "alternative-a", "label": "Alternative A", "type": "Concept"},
                {"id": "cost", "label": "Cost Factors", "type": "Concept"},
            ]
            edges = [
                {"source": "core-topic", "target": "alternative-a", "label": "compared with"},
                {"source": "core-topic", "target": "cost", "label": "influenced by"},
            ]
        return {"nodes": nodes, "edges": edges}

    if response_schema in (FactCheckOutput, FactCheckClaim):
        if topic["laptop"]:
            facts = [
                {
                    "claim": "Unified Memory on MacBook is shared between CPU and GPU, making large LLMs run locally.",
                    "status": "Verified",
                    "explanation": DEMO_NOTE + "Apple Silicon uses Unified Memory Architecture (UMA), which allows both the CPU and GPU to access the same memory pool, letting users run large models locally with 64GB+ of RAM.",
                    "source_link": "https://www.apple.com/newsroom/2023/10/apple-unveils-m3-m3-pro-and-m3-max-chips/",
                },
                {
                    "claim": "The laptop version of the NVIDIA RTX 4090 performs identically to the desktop RTX 4090.",
                    "status": "Debunked",
                    "explanation": DEMO_NOTE + "The mobile RTX 4090 uses the AD103 chip, is capped at 16GB VRAM and ~150W TDP; the desktop RTX 4090 (AD102, 24GB, 450W) is roughly 40-50% faster.",
                    "source_link": "https://www.techpowerup.com/gpu-specs/geforce-rtx-4090-mobile.c3949",
                },
            ]
        elif topic["tesla"]:
            facts = [
                {
                    "claim": "Tesla Model Y was the best-selling car globally in 2023.",
                    "status": "Verified",
                    "explanation": DEMO_NOTE + "Automotive market research (JATO Dynamics) reported the Tesla Model Y as the best-selling vehicle worldwide in 2023.",
                    "source_link": "https://www.jato.com/tesla-model-y-is-the-worlds-best-selling-car/",
                },
                {
                    "claim": "Tesla's Full Self-Driving (FSD) is a Level 5 fully autonomous system.",
                    "status": "Debunked",
                    "explanation": DEMO_NOTE + "Tesla's FSD is classified as an SAE Level 2 driver-assistance system requiring active driver supervision.",
                    "source_link": "https://www.sae.org/blog/sae-j3016-update",
                },
            ]
        elif topic["cs"]:
            facts = [
                {
                    "claim": "Over 70% of professional software developers have a college degree.",
                    "status": "Verified",
                    "explanation": DEMO_NOTE + "Stack Overflow Developer Survey data shows roughly 70-75% of professional developer respondents hold a bachelor's degree or higher.",
                    "source_link": "https://survey.stackoverflow.co/2023/#education",
                }
            ]
        else:
            facts = [
                {
                    "claim": "General claim made in discussion threads.",
                    "status": "Unverified",
                    "explanation": DEMO_NOTE + "Demo mode does not perform live verification.",
                    "source_link": "",
                }
            ]
        if response_schema is FactCheckClaim:
            return facts[0]
        return {"facts_checked": facts}

    if response_schema is IntelligenceReport:
        if topic["laptop"]:
            summary = "For local AI development and machine learning, the choice between Apple macOS and NVIDIA Windows/Linux represents a fundamental trade-off. macOS offers massive Unified Memory (up to 128GB+ on M3/M4 Max), allowing developers to load and run inference on very large LLMs (like Llama-3-70B) directly on a laptop. In contrast, Windows laptops equipped with NVIDIA RTX graphics cards (e.g. RTX 4080/4090 Mobile) are strictly limited to 12GB or 16GB of dedicated VRAM, restricting them to smaller 8B models. However, NVIDIA remains the gold standard for active model training, fine-tuning, and writing raw CUDA code, since PyTorch, JAX, and TensorFlow have superior native optimization for CUDA than Apple's Metal Performance Shaders (MPS)."
            synthesis = """### System Architecture & VRAM Demands

When setting up a machine for local LLMs (Large Language Models), the size of the model you can load is determined entirely by available memory:
* **MacBook Pro (M3/M4 Max):** Can utilize up to 75% of its Unified Memory as VRAM. A 128GB MacBook Pro can dedicate ~96GB to model weights, easily running 70B parameter models at 10-15 tokens per second.
* **NVIDIA Laptops:** The mobile RTX 4090 is limited to 16GB VRAM. This is a hard ceiling: you cannot load a 70B model unless you quantize it heavily or split it across system RAM, which slows inference dramatically.

### The CUDA vs. MPS Dilemma

While macOS rules local *inference* of large models, writing machine learning code is a different story:
1. **CUDA ecosystem:** NVIDIA's CUDA is the undisputed king of ML. Libraries like DeepSpeed, FlashAttention, and custom kernels compile and run natively on CUDA.
2. **MPS (Metal Performance Shaders):** Apple's PyTorch backend is improving but frequently encounters missing operator errors or performance bottlenecks when running training loops or custom neural network architectures.

### Recommendations and Strategy

* **For LLM App Developers / Prompt Engineers:** A MacBook Pro (minimum 64GB RAM) is highly recommended for running and testing large local models without cloud APIs.
* **For ML Researchers / Deep Learning Students:** An NVIDIA laptop (RTX 4070 or 4080) is preferred to learn CUDA and write PyTorch code — or buy a budget laptop and spend the savings on renting cloud GPUs (RunPod, Lambda Labs, Paperspace).
"""
        elif topic["tesla"]:
            summary = "The Reddit community consensus on Tesla ownership is deeply polarized but generally leans positive on technology and infrastructure, while warning about mechanical build quality and customer service. Owners praise the charging experience, noting the Tesla Supercharger network is significantly superior to third-party CCS networks. The software, including the UI and smartphone integration, is considered best-in-class. However, buyers are warned about poor build quality control (panel gaps, paint defects, rattles), high insurance rates, and extremely long wait times at service centers."
            synthesis = """### The Supercharger Advantage
Almost all EV drivers on Reddit agree that Tesla's largest competitive advantage is the Supercharger network. It is reliable, plug-and-play, and widely distributed.

### Build Quality and Reliability
A significant number of Reddit discussions focus on quality control:
* **Interior and panel gaps:** Multiple owners report picking up brand new vehicles with misaligned body panels and interior rattles.
* **Suspension and paint:** Early models are noted for a stiff ride and thin paint that chips easily in snowy climates.

### Financial Depreciation and Insurance
* **High depreciation:** Aggressive price cuts by Tesla have driven down the resale value of used Teslas dramatically.
* **Insurance premiums:** Teslas are expensive to repair after collisions, leading to premium insurance rates.
"""
        elif topic["cs"]:
            summary = "A Computer Science degree remains highly valued in the technology industry, acting as a crucial credential to bypass HR filters and build deep theoretical foundations. However, the current job market is extremely competitive. While a degree is superior to bootcamps or self-taught routes for entering enterprise software engineering and research fields, students are warned that a degree alone is no longer enough. Practical coding experience, internships, and a strong portfolio of projects are mandatory to secure entry-level employment."
            synthesis = """### College Degree vs. Bootcamp and Self-Taught
* **HR filtering:** Automated Applicant Tracking Systems and recruiters heavily favor degree holders; many companies hard-require a Bachelor's in CS or related STEM field.
* **Depth of knowledge:** Degree graduates understand database internals, compiler theory, networking, and operating systems — a real advantage for complex systems work.

### The Debt and Opportunity Cost
* **Tuition fees:** A private or out-of-state university can mean $100k+ in student debt.
* **Alternative strategy:** Attend an affordable state school for the credential while building real-world projects and interview skills in parallel.
"""
        else:
            summary = "The consensus is mixed. The subject provides value under specific conditions, but users need to be aware of the costs and alternatives before committing."
            synthesis = "Detailed synthesis of the topic, breaking down the arguments from the source comments."
        return {
            "consensus_summary": summary,
            "confidence_score": 0.82,
            "detailed_synthesis": synthesis,
        }

    return {}
