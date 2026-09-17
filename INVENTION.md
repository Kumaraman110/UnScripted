# UNSCRIPTED — invention record

Research question: what magical experience exists only because an autonomous intelligence is inside the performance — able to compute over the actual physical state live, search for structure, keep several futures open, and commit late?

Loop: MAKE → PERFORM → ATTACK → BREAK → UNDERSTAND → MUTATE → PERFORM AGAIN. Entries are dated 2026-09-16/17. Numbers come from simulations in `sim/` and `workspace/cards.py` unless marked "live".

---

## v1 (evening show) — DEAD
- **Hypothesis:** a spectator's secret (typed on a phone) + a structure built around it + a hash = prediction.
- **Capability:** generation + hashing.
- **Experiment:** five live attempts in a room of 40 (runs 01:25–02:04) and several solo runs.
- **Failure:** the audience's correct explanation was "the AI built the grid/passage after it learned the secret; the hash proves nothing". Procedural confusion (grid rules), a slipped count, a spectator typing "1" twice.
- **Understanding:** anything Fable constructs after learning a choice is never impossible to an audience that knows Fable exists. A commitment proves existence, not prediction.
- **Mutation:** move the impossibility into physical invariants the spectator does not know, on props they handle; commit before the free act; nothing constructed afterward.

## v2 — classics under a blind performer — SURVIVES AS A BASELINE, NOT THE TARGET
- **Effects:** Gilbreath claim on a Si Stebbins stack (honest "guarantee" framing); Kruskal "Silent Count" on a spectator-shuffled deck; Gemini Twins; clock-count.
- **Live (run 04:35):** both effects landed with the simulator as honest randomness; one false failure caused by Fable's own misaligned check, which Fable then caught in the background and corrected publicly. Zero dead air (background turns 5–7 s).
- **Attack (6-agent panel):** Gilbreath reconstructible by engineers within a minute ("deal off, don't cut" is the tell); Gemini reconstructible as two stack operations; cut-deeper is a false sentence ("you will cut to…"). Kruskal on a read deck survives best because the only reconstruction is "all paths converge", which nobody reaches live.
- **Human test:** a skilled magician can perform all of these (stack, memorized deck, outs). So none is the breakthrough target.

## v2 live run 2 (dinner party, 04:43) — platform validated
- Fable varied the composition for the room (a guest who hates card tricks, a mathematician): clock-count with dinner words in an envelope, then Gemini Twins on the mathematician's shuffle. Eight Fable turns, $1.28, no errors, background turns 5–9 s.
- A deliberate misreport ("3C 8S") routed to the re-read step, the honest re-read continued the effect; both pairs landed. The re-read-before-admitting rule works.

## H1 — FOUND MAGIC: the performance as a visible search (in progress)
- **Hypothesis:** the trick does not exist until the audience creates randomness; Fable searches the actual state for an impossibility, announces the SHAPE it found, locks it, and only then do the free choices happen. Grammar: SHUFFLE → READ → SEARCH → FOUND → LOCK → FREE → LANDING → TWIST.
- **Capability that makes it novel:** live search over rule × direction × start-set × number-of-walkers on a fresh random layout, with a 100% guarantee for every possible secret choice; honest "nothing here, shuffle again" when the search fails; the effect TYPE varies per show and is unknown to the performer.
- **Substrates tried by simulation:** cards (52 face up), audience-written words (letter-count walk), people in a line with dice.
- **Numbers (sim, 3000 shuffles):** see the "feasibility" section below (filled as results land).
- **Adversarial explanation expected:** "all paths converge" (Kruskal). The frame must survive it: the audience should feel "it found a miracle in what we did" rather than "it predicted my number".
- **Open risks:** the announced rule and reading order must be unambiguous; two walkers double the miscount risk; the search must not look like fishing ("shuffle again" more than once is suspicious — cap at one reshuffle, then fall back to a single walker or an honest stop).

### LIVE run 3 (04:56) — The Meeting, first performance
- Fable planned 35 steps in ~6 min pre-show (first step at 35 s). Live: spectator shuffle (sim seed 31337), four rows read, `find_structures` → "two of you will meet", rule announced (pictures 5), K♣ written and covered before any number. Walker 1 secret 9 (row 1), walker 2 secret 3 (row 2): both paths ended on K♣. Independent reconstruction: rows 1–2 all end K♣; rows 3–4 do not — the search was real and specific to this shuffle. 4 Fable turns, $2.17 (planning ~$2), background turns 6–17 s, no dead air.
- **Self-attack:** the skeptic's best line is "the AI saw the layout and computed that walks converge". True and admitted. What remains: the structure was found in *their* shuffle, announced before the free numbers, and no human could have found a guaranteed two-row meeting live. Weakness: for engineers who think of coalescing random walks, the wonder can shrink to "nice math". Mutations under test: let each walker choose their own counting rule; three walkers when available; two independent decks meeting on the same card identity.

### Feasibility (simulation)
- Two walkers (rows 1 and 2, one announced rule): 64% of shuffles. With forward/backward reading choice: 87%.
- Single walker, any 13-card row: 88%.
- Three walkers (rows 1–3): 23%.
- Spectator-authored rule, Fable chooses row and direction: 63%.
- With Fable free to choose direction × rule × rows (sim, 3000 shuffles): THREE walkers meeting available 42.7%; two walkers 35.7%; single walker only 19.9%; nothing 1.7%. → a multi-person meeting exists in ~78% of shuffles; a guaranteed landing of some kind in 98%.

### Mutation results (sim, 3000 shuffles)
- Each walker chooses their OWN counting rule (Fable chooses only direction and rows): two meet 25%, three meet 6% (44% / 11% with one reshuffle). → too weak for a main event; the announced rule stays Fable's.
- Two independent decks, two walkers, same card identity: 13% (mean 2.4 achievable end cards per deck). → parked.
- **EVERYONE MEETS (kept):** whenever two or three rows converge (78% of shuffles), every person in the room may choose any start card in those rows and walk; all fingers land on the covered card. Same guarantee, far stronger experience (mass convergence of independent secret choices), and impossible for a human to guarantee live (an ~85%-per-person Kruskal would fail for someone in any room of 20). Small rooms: two or three named walkers.

### H2 numbers (words, letter-count walk, realistic lengths 3–10)
- P(a converging start block of ≥4 exists, forward or backward): 12 words 2%, 16 words 8%, 20 words 17%, 24 words 26%. Two walkers on 20 words: 1.5%.
- **BROKEN as designed.** Mechanism: word-length steps (3–10) over ~20 items give chains of only 3–5 hops; too few merges. Mutation candidates: (a) walk by letters *inside* the words (letter-by-letter over the concatenated text — chains of 50+ hops converge well, but counting letters across word boundaries is error-prone live); (b) use the words only as the *reveal vocabulary* (destination card ↔ a word) rather than the substrate. Parked.

### H3 numbers (people in a line with dice, first 3–4 starts)
- 10 people 36%, 14 people 57%, 18 people 70%; with one visible re-roll allowed, ~81% at 14 people.
- Feasible but a sharp magician could trace four short chains mentally → fails the human test unless combined with something a human cannot compute live.

## H2 — YOUR WORDS (paper only)
- **Hypothesis:** the audience's own words are the layout; the destination is someone's word.
- **Novelty:** the substrate is created by the audience; the landing is personal ("it's Ben's word").
- **Risk:** convergence on 12–24 words; interactive fix "Fable wants three more words".

## H3 — THE LINE (people and dice)
- **Hypothesis:** the audience is the deck; the landing is a person.
- **Risk:** short chains → weak convergence; a human could trace 4 starts mentally → novelty bar.

## Panel verdicts on H1–H3 (six hostile agents, high effort)
- **Words (H2) and People (H3): FAIL** the human test — "Kruskal on text (Gardner 1978) with the arithmetic outsourced to a phone"; a working mentalist traces the chains in under a minute; the visible re-roll is a tell. Dead.
- **The Meeting (H1): PASSES integrity; novelty borderline (scores 4–6/10).** Old: the walk and the meeting (Kruskal; two-walker analysis by Lagarias–Rains–Vanderbei; performed by Diaconis, Mulcahy). Genuinely new as experience: (1) the trick is provably not in the room before the shuffle; (2) an intelligence announces the SHAPE of the impossibility it found in *this* shuffle ("all of you can meet" / "one of you, blind" / "nothing here"); (3) an exhaustive multi-dimensional search with a guarantee no human can give; (4) the visible refusal of a configuration.
- **Mutations adopted:** everyone walks (mass convergence); the Blind Walk (layout turned face down after the read — physical state known to no one in the room but Fable; the walker explores the unknown and the last card turned is the covered card). Rejected: spectator-chosen rules (25%), two decks (13%), words, people.

## Prior art (web research by the panel, Sept 2026)
- Mechanism: Kruskal count, Gardner/Fulves 1975 (the original is already a two-walk coupling: the magician's hidden walk meets the spectator's ~85%). Mass convergence with 15–20 spectators performed (Nir Dahan). Pre-scanning a specific shuffled deck for its attractor imagined by a human performer (Frank Hood). Two-deck and two-prediction variants published (Thatcher 1986, Otero 2011, Redford 2019). Text Kruskal: Paulos 1999, Gardner 1998, Steinmeyer 2002. Dynkin's blackboard digits demo. Fulves "Kruskal Phone Effect" 1975 (remote magician).
- AI + magic: Williams & McOwan 2014/2017 (AI designs tricks offline); Kwong with ChatGPT as a prop; Mastermind AGT 2025 (AI as theme; forced acrostic); Frack, Pierro, Tempest (AI as theme). **Not found anywhere:** a performance in which the audience is told an autonomous model is the magician, the human is a blind proxy relaying one instruction at a time, and the model computes over the reported physical state to find which effect exists in this state and commits late. Moderate-high confidence this format is undocumented (fringe one-offs may be invisible).
- Honest novelty claim: the format and the live, verified, announced search — never the walk.

## H1 → FINAL FORM: "What your shuffle allows" (the Freedom Budget)
- Fable publishes, verified, what THIS shuffle affords and what it does not (a graded ladder: which rows meet under which settings; near-jackpots with named exceptions; negatives). The audience chooses among verified options before any secret exists; the destination is locked; everyone walks.
- Sim (2000 shuffles): two-row meeting 46%, three-row 41%, four-row 1%; near-jackpot (≥48 of 52 starts) 21%; ≥2 distinct verified options 62%.
- Human test: a human cannot verify 8–24 branches live nor honestly name the exceptions. The skeptic who names Kruskal is answered, not fooled.
- Coda for skeptical rooms: the river — turn down every card no path touches; the channel all paths joined remains visible in their own shuffle.

### LIVE show 5 (05:15, "What your shuffle allows") — the final form performed
- Room: 20 engineers, one who knows Kruskal. Fable planned 31 live steps (pre-show ~6 min; first setup step at 48 s). Deliberate duplicate in a row report → re-read route worked. The ladder read aloud: three verified meetings (A forward pictures=5 rows 1–2 → J♠; B forward pictures=1 rows 1–2 → 5♥; C backward pictures=5 rows 3–4 → 3♥) and two named negatives (no three-row meeting under any rule; no card every start flows to). All three options and the negative verified independently. The room chose C. 3♥ locked under a hand before any choice. Twelve simulated walkers with random starts in rows 3–4, one with a deliberate slip: 12 of 12 on 3♥ (the slip rejoined the channel). Heckler said "Kruskal"; answered with the prepared honest line. Closing written after the fact. 8 Fable turns, $2.46, background turns 5–16 s, no dead air, no errors.

## Verdict against the required conditions
- One-sentence impossibility: "Twenty of us each secretly picked a start in a deck one of us had just shuffled, under a setting we voted for, and every finger ended on the card written under a colleague's hand before anyone chose — and Fable had told us beforehand what this shuffle could and could not do." ✔
- Important choice genuinely free: the shuffle, the setting (among verified options), each person's start. ✔ (Freedom is stated exactly; never "start anywhere" unless verified.)
- Not explicable as "Fable constructed the outcome after learning the choice": the lock precedes every secret; the rule is chosen for the deck and announced; nothing is built after a choice. ✔
- Commitments mean exactly what is claimed: "Fable wrote where the walks end", never "predicted your number". ✔
- Secrets outside the boundary stay unknown: the numbers are never typed. ✔
- Performer does not know the ending: they type rows and write a card Fable dictates. ✔
- Unexpected behavior does not cause deception: misreports → re-read; no meeting → "no meeting in this shuffle"; slips → retrace aloud; misses → honest. ✔ (tested live: duplicate row, slip, heckler)
- No visible AI waiting: background turns 5–16 s while the performer works; checks are instant. ✔ (pre-show planning 5–6 min is private)
- Interaction physical: shuffle, deal, choose, walk a finger, paper under a hand. ✔ (the performer types the layout; the only device)
- Impressive after reconstruction: the skeptic who names Kruskal is told the truth and still cannot name a start that escapes; what remains is the live, verified search and the honest negatives. Panel: passes narrowly on the frame (6/10 new-category from the hostile skeptic). Honest limit: the walk itself is 1975.
- Adaptation, not replay: shows 1–5 differed in effect, ladder, chosen option, and endings; Fable corrected its own check live once and declined a shuffle once. ✔

## Human test, final answer
Could a skilled magician perform essentially this? The landing, yes (Kruskal on a face-up shuffled deck, ~30–85% with outs). The published ladder of verified options and named negatives for THIS shuffle, the audience's choice among them, the honest null, and the blind performer — no. That is the claim, and the only claim.

## Open problems (next mutations)
- The typing of 52 cards (~90 s) is the one visible piece of technology; ritualise it or find a faster honest read.
- Search families beyond walks (a richer library of guaranteed-under-free-choice structures) would make the announced SHAPE less predictable and the frame stronger.
- The river coda (making the channel visible) is untested live.
- Pre-show planning time (5–6 min) could be cut by reusing verified check code across shows.

## Finalist test (to answer for every candidate)
"Could a skilled magician have performed essentially this effect without an autonomous model controlling the performance?" If yes, keep searching.
