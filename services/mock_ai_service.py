import math
import os
import re
from pathlib import Path
from typing import Any

STOPWORDS = frozenset(
    "a an the is are was were be been do does did why what how when where which who whom "
    "we you i they he she it this that these those of in on at to for from with by and or "
    "but not can could would should will about into than then so if as me my our your their "
    "explain tell give describe please".split()
)


def _value(item: Any) -> str:
    return str(getattr(item, "value", item) or "").strip()


def _stems(text: str) -> set[str]:
    words = re.findall(r"[a-z]+", text.lower())
    return {w[:5] for w in words if len(w) >= 3 and w not in STOPWORDS}


class MockAIService:
    def _curriculum_root(self) -> Path:
        configured = os.getenv("CURRICULUM_DIR")
        if configured:
            return Path(configured)
        return Path(__file__).resolve().parent.parent / "curriculum"

    def _lesson_files(self, subject_name: Any, class_level: Any) -> list[Path]:
        root = self._curriculum_root()
        if not root.exists():
            return []

        subject = _value(subject_name).lower()
        level = _value(class_level).lower()
        matches = []
        for path in root.glob("**/lesson.md"):
            parts = [part.lower() for part in path.relative_to(root).parts]
            if level and level not in parts:
                continue
            if subject and subject not in parts:
                continue
            matches.append(path)
        return matches

    def _is_noise(self, line: str) -> bool:
        lower = line.lower()
        return (
            line.startswith(("`", ">", "- **"))
            or "text is extracted from" in lower
            or "page " in lower
            or "smacon" in lower
            or len(line) < 15
            or line.isdigit()
        )

    async def generate_tutor_response(
        self,
        prompt: str,
        subject_name: Any,
        class_level: Any,
        topic_title: str | None = None,
    ) -> dict:
        question_stems = _stems(prompt)
        max_passages = int(os.getenv("MOCK_MAX_PASSAGES", "3"))
        min_ratio = float(os.getenv("MOCK_MIN_MATCH_RATIO", "0.3"))
        if len(question_stems) < 2:
            required = 1
        else:
            required = max(1, math.ceil(len(question_stems) * min_ratio))

        scored: list[tuple[int, int, str]] = []
        seen: set[str] = set()
        order = 0

        for path in self._lesson_files(subject_name, class_level):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue

            # Split by paragraphs to capture full context/definitions instead of isolated single lines
            paragraphs = text.split("\n\n")
            for para in paragraphs:
                cleaned_para = " ".join(
                    line.strip()
                    for line in para.splitlines()
                    if line.strip() and not self._is_noise(line.strip())
                )
                if not cleaned_para or len(cleaned_para) < 30:
                    continue

                key = cleaned_para.lower()
                if key in seen:
                    continue
                seen.add(key)

                score = len(question_stems & _stems(cleaned_para))
                if score >= required:
                    scored.append((score, order, cleaned_para))
                order += 1

        if not scored:
            return {
                "response": (
                    f"### Exploring: {prompt}\n\n"
                    f"Based on your approved curriculum for **{subject_name}** ({class_level}), "
                    "this concept refers to core textbook notes and principles. Take your time reviewing your chapter materials "
                    "to understand how this process functions step-by-step."
                ),
                "model_name": "mock-ai",
                "is_out_of_curriculum": False,
            }

        best = sorted(scored, key=lambda item: (-item[0], item[1]))[:max_passages]
        best.sort(key=lambda item: item[1])
        passages = "\n\n".join(text_block for _, _, text_block in best)

        formatted_response = (
            f"### Answer from your curriculum notes:\n\n"
            f"{passages}\n\n"
            f"*Review this section carefully in your class notes to build complete mastery!*"
        )

        return {
            "response": formatted_response,
            "model_name": "mock-ai",
            "is_out_of_curriculum": False,
        }

    async def generate_assessment(self, *args, **kwargs) -> list[dict]:
        return []

    async def evaluate_assessment(self, *args, **kwargs) -> dict:
        return {
            "accuracy_percentage": None,
            "speed_percentage": None,
            "identified_gaps": [],
            "recommendations": [],
            "corrections": [],
        }
