"""cards.py -- stdlib-only playing-card helper library.

Canonical card representation
------------------------------
A card is a 2-character string: RANK + SUIT.

    RANKS = 'A23456789TJQK'   (A=ace ... T=ten, J=jack, Q=queen, K=king)
    SUITS = 'CDHS'            (clubs, diamonds, hearts, spades)

Examples: '7C' = seven of clubs, 'TH' = ten of hearts, 'QD' = queen of
diamonds, 'AS' = ace of spades.

FULL_DECK is a fixed 52-card list in a stipulated "new deck" order: all
spades A->K, then all hearts A->K, then all clubs A->K, then all diamonds
A->K (i.e. suit cycle 'SHCD', rank cycle 'A23456789TJQK' within each
suit). Any fixed order is fine for these purposes -- this is simply the
one this module documents and uses consistently.

This module has NO side effects on import: no I/O, no top-level random
seeding, nothing but constant/function definitions.

Randomness
----------
Every function that needs randomness accepts an optional ``seed`` (or an
explicit ``rng``/``random.Random`` instance). When a seed/rng is given,
results are fully reproducible. When omitted, a fresh ``random.Random()``
seeded from OS entropy is used internally and results vary run to run.
"""

from __future__ import annotations

import random
import re

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

RANKS = 'A23456789TJQK'
SUITS = 'CDHS'

# Suit order used to build the canonical "new deck" order: spades, hearts,
# clubs, diamonds (documented above).
_NEW_DECK_SUIT_ORDER = 'SHCD'

FULL_DECK = [r + s for s in _NEW_DECK_SUIT_ORDER for r in RANKS]

_SUIT_PRETTY = {'C': '♣', 'D': '♦', 'H': '♥', 'S': '♠'}
_MATE_SUIT = {'C': 'S', 'S': 'C', 'D': 'H', 'H': 'D'}
_RED_SUITS = frozenset('DH')

# --------------------------------------------------------------------------
# Basic card accessors
# --------------------------------------------------------------------------


def rank(card: str) -> str:
    """Return the rank character ('A'..'K') of a canonical card string."""
    return card[0].upper()


def suit(card: str) -> str:
    """Return the suit character ('C','D','H','S') of a canonical card string."""
    return card[1].upper()


def value(card: str) -> int:
    """Return the numeric value of a card's rank: A=1, 2=2, ... T=10, J=11, Q=12, K=13."""
    return RANKS.index(rank(card)) + 1


def color(card: str) -> str:
    """Return 'red' for diamonds/hearts, 'black' for clubs/spades."""
    return 'red' if suit(card) in _RED_SUITS else 'black'


def mate(card: str) -> str:
    """Return the 'mate' of a card: same rank, same color, other suit.

    Clubs <-> Spades, Diamonds <-> Hearts. E.g. mate('7C') == '7S'.
    """
    return rank(card) + _MATE_SUIT[suit(card)]


def pretty(card: str) -> str:
    """Return a human-friendly rendering, e.g. '7C' -> '7♣', 'TH' -> '10♥'."""
    r = rank(card)
    r_text = '10' if r == 'T' else r
    return f"{r_text}{_SUIT_PRETTY[suit(card)]}"


def pretty_list(cards: list) -> str:
    """Return a space-separated pretty rendering of a list of canonical cards."""
    return ' '.join(pretty(c) for c in cards)


# --------------------------------------------------------------------------
# Parsing human input
# --------------------------------------------------------------------------

_RANK_WORDS = {
    'ace': 'A',
    'two': '2', 'three': '3', 'four': '4', 'five': '5',
    'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
    'ten': 'T', 'jack': 'J', 'queen': 'Q', 'king': 'K',
}
_RANK_LETTERS = {'a': 'A', 't': 'T', 'j': 'J', 'q': 'Q', 'k': 'K'}

_SUIT_WORDS = {
    'club': 'C', 'clubs': 'C',
    'diamond': 'D', 'diamonds': 'D',
    'heart': 'H', 'hearts': 'H',
    'spade': 'S', 'spades': 'S',
}
_SUIT_LETTERS = {'c': 'C', 'd': 'D', 'h': 'H', 's': 'S'}
_SUIT_SYMBOLS = {'♣': 'C', '♦': 'D', '♥': 'H', '♠': 'S'}

_FILLER_WORDS = {'of', 'and', 'then', 'top', 'bottom', 'card', 'cards', 'the'}

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[♣♦♥♠]")
_COMBINED_RE = re.compile(r'(10|[a2-9tjqk])([cdhs])')


def _rank_from_token(low: str):
    if low == '10':
        return 'T'
    if low in _RANK_WORDS:
        return _RANK_WORDS[low]
    if low in _RANK_LETTERS:
        return _RANK_LETTERS[low]
    if len(low) == 1 and low in '23456789':
        return low
    return None


def _suit_from_token(tok: str):
    if tok in _SUIT_SYMBOLS:
        return _SUIT_SYMBOLS[tok]
    low = tok.lower()
    if low in _SUIT_WORDS:
        return _SUIT_WORDS[low]
    if low in _SUIT_LETTERS:
        return _SUIT_LETTERS[low]
    return None


# Bare lowercase two-letter forms that are also ordinary English words. They are
# accepted only when the whole report reads as a clean list of cards, so that a
# performer's aside ("..., as best I could see") can never invent the ace of spades.
_AMBIGUOUS_LOWER = {'as', 'ad', 'ah', 'ac'}


def _parse_tokens(tokens, allow_ambiguous):
    """Parse a token list into (cards, indices_consumed)."""
    out, used = [], set()
    i, n = 0, len(tokens)
    while i < n:
        tok = tokens[i]
        low = tok.lower()

        m = _COMBINED_RE.fullmatch(low)
        if m:
            # 'as'/'ad'/'ah'/'ac' typed in lower case are English words as often as cards.
            if not allow_ambiguous and low in _AMBIGUOUS_LOWER and tok != tok.upper():
                i += 1
                continue
            rank_part, suit_letter = m.group(1), m.group(2)
            r = 'T' if rank_part == '10' else _RANK_LETTERS.get(rank_part, rank_part)
            s = _SUIT_LETTERS[suit_letter]
            out.append(r + s); used.add(i)
            i += 1
            continue

        r = _rank_from_token(low)
        # a lone lower-case 'a' before a suit word ("a heart") is prose, not the ace
        if r == 'A' and not allow_ambiguous and tok != 'A' and low == 'a':
            r = None
        if r is not None:
            j = i + 1
            while j < n and tokens[j].lower() in _FILLER_WORDS:
                j += 1
            if j < n:
                s = _suit_from_token(tokens[j])
                if s is not None:
                    out.append(r + s)
                    used.update(range(i, j + 1))
                    i = j + 1
                    continue
            i += 1
            continue

        i += 1

    return out, used


def parse_cards(text: str) -> list:
    """Robustly parse zero or more cards out of free-form human text.

    Accepts, in any mixture, separated by commas/spaces/newlines/other
    punctuation: '7C', '7c', '7 c', '7♣', '10H', 'TH', 'ten of hearts',
    'seven of clubs', 'jack diamonds', 'Q of S', 'ace spades', 'AS'.
    Unicode suit symbols (♣♦♥♠) and suit words (singular or plural,
    case-insensitive) are both understood. Filler words such as 'of', 'and',
    'then', 'top', 'bottom' are ignored. Unparseable tokens are silently
    skipped. Returns canonical 2-character card strings in the order found.

    If the text also contains ordinary prose, the ambiguous lower-case forms
    'as', 'ad', 'ah', 'ac' and 'a <suit>' are NOT read as aces, because
    "…, as best I could see" must not silently become an ace of spades.
    Write 'AS' or 'ace of spades' when you mean the card.
    """
    tokens = _TOKEN_RE.findall(text)
    cards_, used = _parse_tokens(tokens, allow_ambiguous=True)
    leftover = [t for k, t in enumerate(tokens)
                if k not in used and t.lower() not in _FILLER_WORDS and t not in _SUIT_SYMBOLS]
    if leftover:  # the report is not a clean card list — be conservative
        cards_, _ = _parse_tokens(tokens, allow_ambiguous=False)
    return cards_


def leftover_words(text: str) -> list:
    """The tokens in `text` that are neither part of a card nor filler.

    Use this in a report check to notice that a performer typed prose next to
    the cards ("7C KD 3S, the rest were face down"), which usually means the
    report is not what was asked for.
    """
    tokens = _TOKEN_RE.findall(text)
    _, used = _parse_tokens(tokens, allow_ambiguous=True)
    return [t for k, t in enumerate(tokens)
            if k not in used and t.lower() not in _FILLER_WORDS and t not in _SUIT_SYMBOLS]


def parse_card(text: str):
    """Parse a single card out of free-form human text. Returns None if none found."""
    found = parse_cards(text)
    return found[0] if found else None


# --------------------------------------------------------------------------
# Stacks / deck generators
# --------------------------------------------------------------------------


def si_stebbins(top='AC', step=3, suits='CHSD') -> list:
    """Build a 52-card Si Stebbins stack, top->bottom.

    Starting from ``top``, each next card's value increases by ``step``
    (mod 13, using the 1..13 value scale) and its suit advances one step
    through the ``suits`` cycle. The classic stack is
    si_stebbins('AC', 3, 'CHSD') -> AC, 4H, 7S, TD, KC, 3H, 6S, 9D, QC, ...
    """
    is_canonical = (
        isinstance(top, str) and len(top) == 2
        and top[0].upper() in RANKS and top[1].upper() in SUITS
    )
    top_card = top.upper() if is_canonical else parse_card(top)
    if top_card is None:
        raise ValueError(f"could not parse top card: {top!r}")
    s0 = suit(top_card)
    if s0 not in suits:
        raise ValueError(f"top card suit {s0!r} is not in suits cycle {suits!r}")
    start_val = value(top_card)
    start_suit_idx = suits.index(s0)
    ncycle = len(suits)
    deck = []
    for i in range(52):
        val = (start_val - 1 + i * step) % 13
        r = RANKS[val]
        s = suits[(start_suit_idx + i) % ncycle]
        deck.append(r + s)
    return deck


def _rng(seed):
    return seed if isinstance(seed, random.Random) else random.Random(seed)


def alternating_colors(seed=None) -> list:
    """52-card deck where colors strictly alternate red/black top to bottom.

    Within that constraint, which specific card of each color occupies
    each slot is randomized (seeded if ``seed`` given).
    """
    rng = _rng(seed)
    reds = [c for c in FULL_DECK if color(c) == 'red']
    blacks = [c for c in FULL_DECK if color(c) == 'black']
    rng.shuffle(reds)
    rng.shuffle(blacks)
    first, second = (reds, blacks) if rng.choice([True, False]) else (blacks, reds)
    deck = []
    for i in range(26):
        deck.append(first[i])
        deck.append(second[i])
    return deck


def reds_then_blacks(seed=None) -> list:
    """52-card deck: all 26 reds (random order) on top, all 26 blacks (random order) below."""
    rng = _rng(seed)
    reds = [c for c in FULL_DECK if color(c) == 'red']
    blacks = [c for c in FULL_DECK if color(c) == 'black']
    rng.shuffle(reds)
    rng.shuffle(blacks)
    return reds + blacks


def random_deck(seed=None) -> list:
    """A uniformly-shuffled 52-card deck."""
    rng = _rng(seed)
    deck = list(FULL_DECK)
    rng.shuffle(deck)
    return deck


# --------------------------------------------------------------------------
# Deck manipulation
# --------------------------------------------------------------------------


def cut(deck: list, n: int) -> list:
    """Cut ``n`` cards from the top to the bottom. Returns a new list."""
    if not deck:
        return list(deck)
    n = n % len(deck)
    return deck[n:] + deck[:n]


def deal_off(deck: list, n: int):
    """Deal n cards, one at a time, off the top into a new tabled pile.

    Because each dealt card lands on top of the previous one, the packet
    reverses order. Returns (pile_reversed, rest) where ``pile_reversed``
    is top->bottom of the newly dealt packet and ``rest`` is what remains
    of ``deck``.
    """
    n = max(0, min(int(n), len(deck)))  # a negative n must never slice the complement
    top_n = deck[:n]
    rest = deck[n:]
    pile_reversed = list(reversed(top_n))
    return pile_reversed, rest


def riffle(a: list, b: list, rng=None, max_run: int = 4) -> list:
    """Simulate a single realistic riffle shuffle of packets a and b.

    Repeatedly takes a run of 1..max_run cards from the top of whichever
    packet is chosen at random (order within each packet is preserved),
    appending it to the output. Returns the merged deck, top->bottom.
    """
    rng = _rng(rng) if rng is not None else random.Random()
    a = list(a)
    b = list(b)
    out = []
    while a or b:
        if a and b:
            pick_a = rng.choice((True, False))
        else:
            pick_a = bool(a)
        packet = a if pick_a else b
        run = min(rng.randint(1, max(1, max_run)), len(packet))
        out.extend(packet[:run])
        del packet[:run]
    return out


def deal_into_groups(deck: list, size: int) -> list:
    """Split deck into consecutive non-overlapping groups of ``size``, from the top."""
    return [deck[i:i + size] for i in range(0, len(deck), size)]


# --------------------------------------------------------------------------
# Checks (Gilbreath-style)
# --------------------------------------------------------------------------


def _first_failing_group(deck: list, size: int, key):
    for idx, i in enumerate(range(0, len(deck), size)):
        group = deck[i:i + size]
        if len(group) < size:
            break  # an incomplete trailing group proves nothing; never count it as a pass
        keys = [key(c) for c in group]
        if len(set(keys)) != len(keys):
            return idx
    return None


def groups_all_distinct(deck: list, size: int, key) -> bool:
    """True if every consecutive group of ``size`` cards from the top has all-distinct key(card) values.

    ``key`` is typically the ``suit`` or ``rank`` function from this module.
    """
    return _first_failing_group(deck, size, key) is None


def gilbreath_report(deck: list) -> dict:
    """Convenience report for the two classic Gilbreath checks. FULL 52-CARD DECK ONLY.

    Returns 'suits4_ok' / 'ranks13_ok' plus the index of the first failing group
    of 4 (by suit) / of 13 (by rank), or None if none failed, plus how many
    complete groups were actually examined.

    An '_ok' flag is only evidence when its '_groups_checked' count is above
    zero: four dealt cards contain no complete group of thirteen, so nothing
    about ranks has been proven. For a partial deal during a reveal, use
    gilbreath_reveal_check(dealt_so_far) instead, which checks exactly the
    aligned groups that are complete.
    """
    fail4 = _first_failing_group(deck, 4, suit)
    fail13 = _first_failing_group(deck, 13, rank)
    return {
        'suits4_ok': fail4 is None,
        'ranks13_ok': fail13 is None,
        'suits4_first_fail_group': fail4,
        'ranks13_first_fail_group': fail13,
        'suits4_groups_checked': len(deck) // 4,
        'ranks13_groups_checked': len(deck) // 13,
    }


# ---------------- Kruskal count on a face-up layout ----------------
KRUSKAL_RULES = {
    'court5': 'Ace=1, number cards face value, Jack/Queen/King = 5',
    'court1': 'Ace=1, number cards face value, Jack/Queen/King = 1',
    'court10': 'Ace=1, number cards face value, Jack/Queen/King = 10',
    'jqk': 'Ace=1, number cards face value, Jack=11, Queen=12, King=13',
}

def kruskal_value(card, rule='court5'):
    """Step size for a card under a Kruskal rule."""
    r = rank(card)
    if r == 'A': return 1
    if r == 'T': return 10
    if r in 'JQK':
        return {'court5': 5, 'court1': 1, 'court10': 10, 'jqk': {'J': 11, 'Q': 12, 'K': 13}[r]}[rule]
    return int(r)

def kruskal_chain(layout, start, rule='court5'):
    """Positions visited (1-based) starting at `start` in a face-up layout read in order.
    From a card, move forward by its value; stop when the next move would leave the layout."""
    i = start - 1
    chain = [i + 1]
    while True:
        j = i + kruskal_value(layout[i], rule)
        if j >= len(layout): return chain
        i = j; chain.append(i + 1)

def kruskal_end(layout, start, rule='court5'):
    """The final card landed on from `start` (1-based)."""
    return layout[kruskal_chain(layout, start, rule)[-1] - 1]

def kruskal_prefix(layout, rule='court5', max_start=13):
    """Largest N such that every start 1..N ends on the same card. Returns (N, end_card)."""
    end = kruskal_end(layout, 1, rule); n = 1
    while n < max_start and kruskal_end(layout, n + 1, rule) == end: n += 1
    return n, end

def best_kruskal(layout, max_start=13, rules=('court5', 'jqk', 'court10', 'court1')):
    """Pick the rule giving the longest all-converging prefix. Returns dict(rule, description, N, end)."""
    best = None
    for r in rules:
        n, end = kruskal_prefix(layout, r, max_start)
        if best is None or n > best['N']: best = {'rule': r, 'description': KRUSKAL_RULES[r], 'N': n, 'end': end}
    return best


# ---------------- Gilbreath reveal checking (use this; do not hand-roll alignment) ----------------
def gilbreath_reveal_check(dealt):
    """`dealt` = ALL cards dealt so far from the top of the riffled deck, in order (card 1 first).
    Checks ONLY the aligned groups that are complete: suits on cards 1-4, 5-8, 9-12, ...; values on 1-13, 14-26, 27-39, 40-52.
    Groups of four inside the SECOND row of thirteen (cards 14-26) are NOT aligned and must not be checked as suit groups.
    Returns dict(ok, suit_groups_checked, value_groups_checked, first_bad) where first_bad describes the first failing group or None."""
    res = {'ok': True, 'suit_groups_checked': 0, 'value_groups_checked': 0, 'first_bad': None}
    for g in range(len(dealt) // 4):
        grp = dealt[g * 4:(g + 1) * 4]
        res['suit_groups_checked'] += 1
        if len({suit(c) for c in grp}) != 4:
            res['ok'] = False; res['first_bad'] = res['first_bad'] or f'cards {g*4+1}-{g*4+4} suits {grp}'
    for g in range(len(dealt) // 13):
        grp = dealt[g * 13:(g + 1) * 13]
        res['value_groups_checked'] += 1
        if len({rank(c) for c in grp}) != 13:
            res['ok'] = False; res['first_bad'] = res['first_bad'] or f'cards {g*13+1}-{g*13+13} values {grp}'
    return res

SUIT_NAMES = {'C': 'Club', 'D': 'Diamond', 'H': 'Heart', 'S': 'Spade'}

def suit_name(s, plural=False):
    """'H' -> 'Heart' ('Hearts' if plural). Use this whenever a suit letter is going to be
    spoken aloud by the performer, so a step never reads 'the fourth card is a H'."""
    n = SUIT_NAMES.get((s or '').upper()[:1])
    return None if n is None else (n + 's' if plural else n)

def missing_suit(three):
    """The suit missing from three cards of distinct suits (for the live 'fourth card' beat), or None."""
    s = {suit(c) for c in three}
    if len(s) != 3: return None
    return ({'C', 'D', 'H', 'S'} - s).pop()


# ---------------- Found magic: search a face-up layout for guaranteed meeting structures ----------------
def physical_row(row_index, direction, n_rows=4):
    """Convert a row index used by the walk into the row the audience is looking at.

    A 'forward' reading starts at the top-left card, so its row 0 is the top row.
    A 'backward' reading starts at the LAST card, so its row 0 is the BOTTOM row.
    Returns a 1-based row number counted from the top, which is the only way a
    row may ever be described out loud.
    """
    return row_index + 1 if direction == 'forward' else n_rows - row_index


def find_structures(layout, rules=('court5', 'jqk', 'court10', 'court1'), rows=4, row_len=13):
    """Search a 52-card face-up layout (reading order) for structures that hold for EVERY possible secret start.
    Returns a list of dicts ranked strongest first. Each has: kind ('three'|'two'|'single'), direction ('forward'|'backward'),
    rule, rule_text, rows (0-based row indices offered to the walkers, in walker order), end (the card everyone lands on), n_starts.
    'backward' means the layout is read from the LAST card toward the first (announce it as such: start on the bottom row,
    move toward the beginning). Use the top-ranked entry; if the list is empty, ask for a reshuffle."""
    if len(layout) != rows * row_len:
        raise ValueError(f'layout must be exactly {rows * row_len} cards, got {len(layout)}')
    out = []
    for direction, lay in (('forward', list(layout)), ('backward', list(layout)[::-1])):
        ends = {}
        for r in rules:
            for row in range(rows):
                ends[(r, row)] = {kruskal_end(lay, s, r) for s in range(row * row_len + 1, row * row_len + row_len + 1)}
        for r in rules:
            good = [row for row in range(rows) if len(ends[(r, row)]) == 1]
            # group rows by shared end
            by_end = {}
            for row in good: by_end.setdefault(next(iter(ends[(r, row)])), []).append(row)
            for end, rs in by_end.items():
                rs = sorted(rs)
                kind = 'all' if len(rs) >= 4 else 'three' if len(rs) == 3 else 'two' if len(rs) == 2 else 'single'
                out.append({'kind': kind, 'direction': direction, 'rule': r, 'rule_text': KRUSKAL_RULES[r],
                            'rows': rs, 'rows_physical': [physical_row(x, direction, rows) for x in rs],
                            'end': end, 'n_starts': row_len * len(rs)})
    rank = {'all': 0, 'three': 1, 'two': 2, 'single': 3}
    out.sort(key=lambda o: (rank[o['kind']], o['direction'] != 'forward', o['rule'] != 'court5'))
    return out

def walk_positions(layout, start, rule='court5', direction='forward'):
    """1-based positions visited in the ORIGINAL layout order for a walker starting at 1-based `start` of the given direction's reading."""
    lay = list(layout) if direction == 'forward' else list(layout)[::-1]
    chain = kruskal_chain(lay, start, rule)
    if direction == 'forward': return chain
    n = len(layout); return [n - p + 1 for p in chain]


# ---------------- The Freedom Budget: what THIS shuffle affords, verified ----------------
READING_TEXT = {
    'forward': 'reading like a book: left to right, and at the end of a row carry on at the LEFT end of the row below',
    'backward': 'reading backwards: right to left, and at the left end of a row carry on at the RIGHT end of the row above',
}


def freedom_ladder(layout, rules=('court5', 'jqk', 'court10', 'court1')):
    """For a 52-card face-up layout, compute every verified option the audience may be offered.
    Returns dict with:
      options: list of {direction, rule, rule_text, end, rows_all (0-based rows where EVERY start converges to end),
                        flow_starts (1-based start positions, in that direction's reading, that reach end),
                        exceptions_in_rows (cards in rows_all-adjacent region that do not flow — informational)}
               sorted by len(rows_all) desc then forward first.
      jackpot: an option where ALL 52 starts flow to one card (or None).
      near_jackpot: option with >= 48 flowing starts, with the list of exception cards (or None).
      negatives: human-readable list of what this shuffle does NOT afford (e.g., 'no three-row meeting forward with pictures=5').
    Directions: 'forward' = reading order; 'backward' = from the last card toward the first."""
    if len(layout) != 52:
        raise ValueError(f'layout must be exactly 52 cards, got {len(layout)}')
    out = []; negatives = []
    for direction, lay in (('forward', list(layout)), ('backward', list(layout)[::-1])):
        for r in rules:
            ends = [kruskal_end(lay, s, r) for s in range(1, 53)]
            from collections import Counter
            dom, cnt = Counter(ends).most_common(1)[0]
            flow = [s for s in range(1, 53) if ends[s - 1] == dom]
            rows_all = [row for row in range(4) if all(ends[s - 1] == dom for s in range(row * 13 + 1, row * 13 + 14))]
            exceptions = [lay[s - 1] for s in range(1, 53) if ends[s - 1] != dom]
            out.append({'direction': direction, 'rule': r, 'rule_text': KRUSKAL_RULES[r], 'end': dom, 'rows_all': rows_all,
                        'rows_physical': sorted(physical_row(x, direction) for x in rows_all),
                        'reading': READING_TEXT[direction],
                        'n_flow': cnt, 'flow_starts': flow, 'exceptions': exceptions})
    out.sort(key=lambda o: (-len(o['rows_all']), o['direction'] != 'forward', -o['n_flow']))
    jackpot = next((o for o in out if o['n_flow'] == 52), None)
    near = next((o for o in out if 48 <= o['n_flow'] < 52), None)
    best_rows = max(len(o['rows_all']) for o in out)
    if best_rows < 3: negatives.append('no three-row meeting under any of the four rules, either direction')
    if best_rows < 2: negatives.append('no two-row meeting under any rule, either direction')
    if not jackpot: negatives.append('no card that every single start flows to')
    return {'options': out, 'jackpot': jackpot, 'near_jackpot': near, 'negatives': negatives, 'best_rows': best_rows}

def describe_ladder(ladder, max_options=6):
    """Plain-language summary lines Fable can read aloud (verified options only)."""
    lines = []
    L = ladder
    if L['jackpot']: o = L['jackpot']; lines.append(f"JACKPOT: reading {o['direction']} with {o['rule_text']}, every one of the 52 cards flows to {pretty(o['end'])} — start anywhere.")
    elif L['near_jackpot']: o = L['near_jackpot']; lines.append(f"Reading {o['direction']} with {o['rule_text']}: start anywhere except {', '.join(pretty(c) for c in o['exceptions'])} — all flow to {pretty(o['end'])}.")
    for o in L['options'][:max_options]:
        if o['rows_all']:
            rows = ', '.join(f"row {r}" for r in o['rows_physical'])
            lines.append(f"{o['rule_text']}, {o['reading']}: every start in {rows} (counting rows from the top) "
                         f"ends on {pretty(o['end'])} ({o['n_flow']} of 52 starts flow there).")
    for n in L['negatives']: lines.append('NOT available: ' + n)
    return lines
