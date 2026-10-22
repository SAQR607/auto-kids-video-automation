Write the COMPLETE episode package JSON for this premise:

__PREMISE_JSON__

OUTPUT SHAPE (strict):
- scenes array MUST contain EXACTLY 13 scene objects, ids sc01..sc13.
- EXACTLY 5 dialogue lines per scene (each 9-11 words) + EXACTLY 1 narration block of 35-40 words.
- That is 80-95 spoken words per scene; AIM FOR ~87 words per scene (~1130 total). Hard limits: total 980-1230 words, estimated duration 420-540s — scripts under ~1030 words are rejected as sparse, so never write thin scenes.
- Output MINIFIED JSON: one line, no indentation, no newlines outside strings.
- The example shows only ONE scene for style — it is NOT the output size.

EXAMPLE SCENE (style — shows ONE scene, not the output size; your real scenes need ALL 5 dialogue lines + full 35-40 word narration):
{"scene_id":"sc03","location":"market_square","time_of_day":"day","camera":"static","transition_in":"fade","music_mood":"discovery","characters":[{"id":"stik","position":"left","enter":"onscreen","state":"idle"},{"id":"dot","position":"right","enter":"onscreen","state":"idle"}],"dialogue":[{"speaker":"stik","text":"This square once traded in spices from three continents.","emotion":"curious","action":"gestures at the stalls"},{"speaker":"dot","text":"And all of it crossed the sea by wooden ship?","emotion":"surprised","action":"points at the river"},{"speaker":"stik","text":"Rowed, sailed, and carried by hand for weeks.","emotion":"determined","action":"traces the route on the scroll"},{"speaker":"dot","text":"No engines back then - just wind and patience.","emotion":"proud","action":"nods slowly"},{"speaker":"stik","text":"Watch closely, Dot - the market is about to open.","emotion":"happy","action":"unrolls the scroll"}],"narration":[{"text":"Long before warehouses and railways, markets like this one were the internet of their age. News, prices, and ideas all arrived by the same dusty road, carried by merchants who measured the world one journey at a time."}],"props":["scroll"],"fx":[]}

FIELD RULES:
- Scene order follows the beat template above; learning spine shown by actions in payoff scenes.
- Each scene: scene_id, location, time_of_day (EXACTLY one of day/morning/dusk/night — never dawn, noon, evening, twilight), camera, transition_in, music_mood, characters, dialogue, narration, props, fx.
- music_mood MUST be exactly one of the music_moods ids in ALLOWED IDS — never invent one ('endcard', 'credits', 'outro' are NOT valid ids).
- characters: 1-2 objects {"id": "stik" or "dot", "position": left/center/right/far_left/far_right, "enter": onscreen/enter_left/enter_right, "state": initial sprite state}. At least one scene early on must show BOTH stik and dot together; both must speak somewhere in the episode.
- dialogue entry: {"speaker": "stik" or "dot", "text": "9-11 words (hard limits 5-14 — never 2-4 word exclamations)", "emotion": expression id, "action": "physical action <=8 words"}.
- CTA (required, verbatim): the LAST dialogue entry of the FINAL scene (sc13) is exactly {"speaker":"stik or dot","text":"__CTA_TEXT__","emotion":"__CTA_EMOTION__","action":"__CTA_ACTION__"} — it replaces the 5th dialogue line; never reword or omit it.
- sc13 is a NORMAL full scene, NOT an end card: 1-2 characters on screen, a regular music_mood from the allowed list, full 5 dialogue lines + 35-40 word narration. The CTA line simply IS its 5th dialogue entry.
- EXPRESSIONS (closed list): __EXPRESSIONS__. emotion MUST be exactly one of these — the sprite sheet has no others. NEVER invent synonyms (calm, confused, thoughtful, angry, scared); one invented emotion rejects the whole script.
- narration: [{"text": "35-40 words"}]. Narration carries the history: plain language, well-known facts only, minimal dates, no invented quotes presented as real.
- props = physical objects ONLY from the PROPS list (scroll, oil_lamp, jug, basket, crate, oar, hammer, ladder, lantern, signpost). fx = visual effects (glimmer_sparkle, leaf_swirl, ...) from the fx list. NEVER put fx ids, location ids or invented items in "props" — every prop id must exist in the PROPS list or the script is rejected.
- arc_crumb must be null: this series has no season arc.
- Exactly 2 shorts, SELF-CONTAINED for vertical 1080x1920 (no references to the long episode): they tell one complete tiny story on their own.
  {"short_id":"short_1","kind":"<assigned mood>","title":"<=40 chars","location":id,"time_of_day":"day/morning/dusk/night","camera":"...","characters":["EXACTLY 1-2 ids: stik and/or dot"],"dialogue":[{"speaker":"...","text":"...","emotion":"expression from EXPRESSIONS","action":"..."}],"music_mood":"...","duration_target_sec":34}
  EXACTLY 6 dialogue lines each (10-16 words), 60-96 spoken words total per short.
- metadata: {"title":"<=70 chars: '<topic search phrase> | Stickman Stories' — a curiosity/search-first phrase about the topic FIRST (e.g. 'How the Great Wall Was Built' or 'The Lost Library of Alexandria'), then ' | Stickman Stories' EXACTLY as the last two words; never an episode code (no S1E__)","description":"<=500 chars: FIRST sentence uses an animated-history search phrase naturally (e.g. 'An animated history story about <topic> from Stickman Stories') + what happens in the episode + the series line 'Stickman Stories - animated stick-figure retellings of history's greatest stories' + schedule line exactly 'New stories every Sunday, Tuesday and Thursday; new shorts every Saturday.' You may add one short like/subscribe nudge. No links.","tags":["8-12 tags starting with: animated history, history stories, animated history videos, world history, history explained, stick figure animation, stickman stories, historical stories - plus 0-4 episode-theme tags (e.g. ancient egypt, vikings, roman empire)"]}
- Top-level "title": curiosity title WITHOUT the series suffix (<=62 chars).

Return ONLY the JSON with ALL top-level keys:
schema ("stickman.episode/1"), episode_id, title, premise, learning_spine,
duration_target_sec, hook, arc_crumb (null), thumbnail_concept (copy the
object from the premise above), scenes, shorts (exactly 2),
metadata, callbacks_available (<=3 strings or []).
