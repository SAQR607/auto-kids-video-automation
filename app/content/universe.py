"""Universe context: condensed writer's brief built from manifest + rules.

Note: universe/*.md bibles are the HUMAN source of truth; this module distils
the binding rules into a compact prompt block (Groq request-size limit ~32KB,
so full bibles cannot be embedded verbatim).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import ROOT
from ..logging_setup import get_logger

log = get_logger("universe")

SPINES = [
    "patience", "sharing", "honesty", "asking for help", "trying again",
    "listening", "kindness to small things", "keeping promises",
    "courage with care", "gratitude", "including others", "caring for nature",
    "telling the truth first", "waiting your turn",
]

SHORT_MOODS = ["funny", "wonder", "heart", "music", "surprise", "playful"]

# Parent-facing end-of-video CTA (docs/YOUTUBE_GROWTH.md §7): spoken as the
# LAST dialogue line of the final scene. Made-for-kids safe — addresses the
# grown-ups watching, not the child viewer. Wording is fixed and QC-enforced;
# it is exempt from the dialogue word-ban scan (it contains "subscribe").
CTA_TEXT = "Grown-ups, a gentle like and subscribe help our meadow glow brighter."
CTA_EMOTION = "happy"
CTA_ACTION = "waves to the viewer"

# Season-1 arc crumb per long episode number (WORLD_BIBLE table; 1-based).
ARC_CRUMBS: dict[int, str] = {
    1: "First Glimmer lights drift over Glimmer Meadow right after Juni's small act of help (visual only, wonder beat).",
    2: "Glimmer does NOT appear when a character shows off; it appears later when they help quietly (compare two moments).",
    3: "Wren maps the glow spots; the pattern of dots on her map points east.",
    4: "A glowing compass stone is found beneath the third stepping stone in Whispering Stream; it tugs gaze east.",
    5: "The compass stone's glow points at the sealed root-door of Glimmer Cave (door does not open).",
    6: "Brightness test: glow is brighter when more friends help together — measured with Wren's stick.",
    7: "A faint melodic hum drifts from Glimmer Cave at dusk — the four-note Glimmer motif.",
    8: "Willowby's oldest book mentions 'the valley's ledger of kindness' — a written clue.",
    9: "Pebble stacks appear overnight on Glimmer Meadow — someone else is leaving thanks.",
    10: "The stack-builder is Fern — gathering stones to thank the Glimmer for kindness received.",
    11: "A storm drizzle washes out the path; four friends rebuild it together and the glow surges brighter.",
    12: "All four friends touch the root-door together and it stirs open a hand's width.",
    13: "Inside: the heart-stone glowing with accumulated kindness — and one unanswered new question for Season 2.",
}

WORLD_RULES = """# FERNWOOD WORLD (condensed, binding)
- Hidden woodland valley; friends live in/around Hollow Oak Village. No money, shops, or electricity.
- THE GLIMMER: soft lights rise from Glimmer Meadow on real kindness, courage or honesty. Never frightens, never punishes, grants no wishes — only responds. Brighter when more friends help together.
- Conflict only: misunderstanding, lost objects, mild weather, self-doubt. NO villains, weapons, fear, storms-as-drama.
- Solutions: kindness, observation, teamwork or a clever tool. Every question answered inside the episode."""

BEAT_TEMPLATE = """# BEAT TEMPLATE (540s target, scenes in this arc order)
1 Cold open/hook (motion+voice in first 10s) -> 2 everyday setup -> 3 mild problem -> 4 first try (instructive partial fail) -> 5 re-think (observe, ask) -> 6 better plan (teamwork+tool) -> 7 payoff (success, learning lands) -> 8 warm close (joke callback, friendship, optional arc flicker) -> 9 farewell wave (a NORMAL scene: 2-4 friends on screen together, standard structure and music mood — never a solo "end card").
- EXACTLY 14 scenes. One learning spine, shown by action, never lectured.
- Every scene: 2-4 characters. Willowby only asks questions, never solves."""

DIALOGUE_RULES = """# DIALOGUE + CONTENT RULES
- Child characters: sentences <=10 words. Willowby <=14. One idea per line.
- Repeat the key learning phrase once. Name the speaker's friends naturally.
- BANNED: danger, scary, monster, kill, hate, stupid, buy, subscribe, comment, discount, weapon, gun, fight, mean, laugh at, shut up, die, freak, weirdo.
- Warm, curious, gently funny. Problem resolved inside the episode. No cliffhangers.
- Narration only bridges scenes; emotion lives in dialogue."""

# Per-profile prompt text overrides live in the manifest under "rules"
# (writer_system, brief) or as <universe_dir>/brief.md for the large script
# brief. Empty string = "no override" (prompts fall back to their defaults).

class Universe:
    """Content identity for one channel profile.

    Data source: <universe_dir>/manifest.json. Every prompt-facing rule is an
    instance attribute: the manifest may override it under a top-level
    "rules" key ({spines, short_moods, cta: {text, emotion, action},
    arc_crumbs, world_rules, beat_template, dialogue_rules,
    writer_system, brief}) — absent keys fall back to the Fernwood defaults
    above, so the default profile behaves exactly as before. The full script
    brief can also come from <universe_dir>/brief.md (takes precedence over
    manifest rules.brief), because it is large hand-edited prose.
    """

    def __init__(self, root: Path | None = None, *, universe_dir: Path | None = None):
        self.root = root or ROOT
        self.universe_dir = universe_dir or (self.root / "universe")
        self.manifest: dict[str, Any] = json.loads(
            (self.universe_dir / "manifest.json").read_text(encoding="utf-8")
        )
        rules = self.manifest.get("rules") or {}
        self.spines: list[str] = [str(s) for s in (rules.get("spines") or SPINES)]
        self.short_moods: list[str] = [str(m) for m in (rules.get("short_moods") or SHORT_MOODS)]
        cta = rules.get("cta") or {}
        self.cta_text: str = str(cta.get("text") or CTA_TEXT)
        self.cta_emotion: str = str(cta.get("emotion") or CTA_EMOTION)
        self.cta_action: str = str(cta.get("action") or CTA_ACTION)
        self.arc_crumbs: dict[int, str] = {
            int(k): str(v) for k, v in (rules.get("arc_crumbs") or ARC_CRUMBS).items()
        }
        self.world_rules: str = str(rules.get("world_rules") or WORLD_RULES)
        self.beat_template: str = str(rules.get("beat_template") or BEAT_TEMPLATE)
        self.dialogue_rules: str = str(rules.get("dialogue_rules") or DIALOGUE_RULES)
        self.writer_system: str = str(rules.get("writer_system") or "")
        brief_md = self.universe_dir / "brief.md"
        if brief_md.exists():
            self.brief: str = brief_md.read_text(encoding="utf-8")
        else:
            self.brief = str(rules.get("brief") or "")

    @property
    def character_ids(self) -> list[str]:
        return [c["id"] for c in self.manifest["characters"]]

    @property
    def location_ids(self) -> list[str]:
        return [l["id"] for l in self.manifest["locations"]]

    @property
    def prop_ids(self) -> list[str]:
        return list(self.manifest["props"])

    @property
    def voices(self) -> dict[str, str]:
        return {c["id"]: c.get("voice", "af_bella") for c in self.manifest["characters"]}

    def main_characters(self) -> list[str]:
        return [c["id"] for c in self.manifest["characters"] if c.get("main")]

    def character_summary(self) -> str:
        lines = []
        for c in self.manifest["characters"]:
            tag = "MAIN" if c.get("main") else "recurring"
            line = f"- {c['id']} ({c['display_name']}, {c['species']}, {tag}): {c.get('personality', '')}"
            lines.append(line)
        return "\n".join(lines)

    def location_summary(self) -> str:
        return "\n".join(
            f"- {l['id']}: {l.get('blurb', l['name'])}" for l in self.manifest["locations"]
        )

    def manifest_ids(self) -> str:
        m = self.manifest
        # expressions are omitted here: script generation already injects the
        # closed list via the SCRIPT_BRIEF __EXPRESSIONS__ placeholder, so
        # including them again wastes precious TPM-input tokens (free tier is
        # input+max_tokens-bound). Premise generation never needs expressions.
        # characters/locations are omitted here too: character_summary() and
        # location_summary() already list every id (with blurbs), so the bare
        # id lists are pure duplication. Only the compact closed vocabularies
        # that have no other prompt presence are kept.
        return json.dumps({
            "props": m["props"],
            "fx": m["fx"],
            "camera_moves": m["camera_moves"],
            "transitions": m["transitions"],
            "positions": m["positions"],
            "entrances": m["entrances"],
            "music_moods": m["music_moods"],
        })

    def context_block(self, *, include_arc: bool, arc_crumb: str | None) -> str:
        parts = [
            self.beat_template,
            self.dialogue_rules,
            "# CHARACTERS\n" + self.character_summary(),
            "# LOCATIONS (use only these ids)\n" + self.location_summary(),
            "# ALLOWED IDS\n" + self.manifest_ids(),
        ]
        if include_arc:
            parts.append(self.world_rules)
            parts.append(f"# REQUIRED ARC CRUMB THIS EPISODE\n{arc_crumb}")
        else:
            parts.append(
                "# ARC RULE\nThis episode does NOT advance the season mystery: "
                "no cave, no compass stone, no pebble stacks, no arc teases. arc_crumb = null."
            )
        return "\n\n".join(parts)
