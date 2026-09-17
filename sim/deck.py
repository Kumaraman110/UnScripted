#!/usr/bin/env python3
"""sim/deck.py -- a CLI "physical table" simulator for card magic testing.

This program lets a tester act honestly as the physical world: piles of
cards live in sim/state.json, each card in a pile carries a face-up/down
flag, and every command below is meant to correspond to something a real
spectator or performer could do with a real deck on a real table. There
is no secret state: any command that looks at card identities (top,
bottom, spread, neighbors, groups) is explicitly a peek, and says so.

Usage: python3 sim/deck.py <command> [args...]

Commands
--------
  new [sistebbins|random|alt|redblack|newdeck] [--seed N] [--top AC]
        Create pile 'deck' (replaces all table state).
  shuffle <pile>
        Full random shuffle (overhand/wash equivalent).
  cut <pile> [n]
        Cut n cards from top to bottom (random 10-40 if n omitted).
  dealoff <from> <to> <n>
        Deal n cards one at a time from top of <from> onto <to> (reverses
        their order), face down. <to> is created if it doesn't exist.
  riffle <a> <b> <into> [--max-run 4]
        Single riffle of piles a and b into a new pile <into>; a and b
        are consumed.
  top <pile> [n]
        PEEK: show the top n cards (default 1), pretty-printed.
  bottom <pile> [n]
        PEEK: show the bottom n cards (default 1), pretty-printed.
  deal <from> <to> <n> [--faceup]
        Deal n cards one at a time from top of <from> onto <to>
        (reverses their order), face up if --faceup else face down.
  place <card> <pile> [--faceup]
        Remove a specific card from wherever it is on the table and put
        it on top of <pile>.
  drop <from> <onto>
        Put the entire <from> pile on top of <onto>, preserving relative
        order; <from> is deleted.
  flip <pile>
        Turn the whole pile over as a unit: order reverses and every
        card's face flag toggles.
  spread <pile>
        PEEK: print every card top->bottom with its index, marking
        face-up cards with '*'.
  neighbors <card> <pile>
        PEEK: print the card directly above (toward top) and below
        (toward bottom) the given card within <pile>.
  groups <pile> <size>
        PEEK: print consecutive groups of <size> cards from the top of
        <pile>, each flagged for suit-distinct / rank-distinct.
  state
        Print pile names and counts only (no card identities -- not a
        peek).

Randomness
----------
`new` creates a fresh random.Random, seeded with --seed if given, else
from OS entropy. Its internal state is persisted into state.json's
"rng_state" field. Every later command that needs randomness (shuffle,
cut without an explicit n, riffle's interleave choices) loads that same
persisted RNG, uses it, and saves its (now-advanced) state back. That
means an entire session -- from `new --seed 42` through any sequence of
commands -- is fully reproducible by replaying the same commands in the
same order. If state.json has no rng_state (e.g. it was hand-edited),
commands fall back to a fresh OS-entropy RNG for that single invocation.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'workspace'))
import cards  # noqa: E402

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'state.json')


# --------------------------------------------------------------------------
# State I/O
# --------------------------------------------------------------------------

def load_state():
    if not os.path.exists(STATE_PATH):
        return None
    with open(STATE_PATH, 'r') as f:
        return json.load(f)


def save_state(state):
    with open(STATE_PATH, 'w') as f:
        json.dump(state, f, indent=2)


def require_state():
    state = load_state()
    if state is None:
        print("No table state yet. Run 'new' first (e.g. `python3 sim/deck.py new random --seed 1`).")
        sys.exit(1)
    return state


def get_rng(state):
    """Load the persisted RNG if present, else a fresh OS-entropy RNG."""
    blob = state.get('rng_state')
    if blob is None:
        return random.Random()
    rng = random.Random()
    version, internal, gauss_next = blob
    rng.setstate((version, tuple(internal), gauss_next))
    return rng


def put_rng(state, rng):
    version, internal, gauss_next = rng.getstate()
    state['rng_state'] = [version, list(internal), gauss_next]


# --------------------------------------------------------------------------
# Small helpers over piles (list of {'c': code, 'up': bool})
# --------------------------------------------------------------------------

def _entry(code, up=False):
    return {'c': code, 'up': bool(up)}


def _codes(entries):
    return [e['c'] for e in entries]


def _reorder(entries, new_codes):
    lookup = {e['c']: e for e in entries}
    return [lookup[c] for c in new_codes]


def _pile(state, name):
    return state.setdefault('piles', {}).setdefault(name, [])


def _find_card(state, code):
    """Return (pile_name, index) of a card anywhere on the table, or (None, None)."""
    for name, entries in state.get('piles', {}).items():
        for i, e in enumerate(entries):
            if e['c'] == code:
                return name, i
    return None, None


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_new(args):
    rng = random.Random(args.seed) if args.seed is not None else random.Random()
    kind = args.kind or 'newdeck'

    if kind == 'sistebbins':
        deck_codes = cards.si_stebbins(top=args.top)
    elif kind == 'random':
        deck_codes = list(cards.FULL_DECK)
        rng.shuffle(deck_codes)
    elif kind == 'alt':
        derived_seed = rng.randrange(2 ** 32)
        deck_codes = cards.alternating_colors(seed=derived_seed)
    elif kind == 'redblack':
        derived_seed = rng.randrange(2 ** 32)
        deck_codes = cards.reds_then_blacks(seed=derived_seed)
    else:  # newdeck
        deck_codes = list(cards.FULL_DECK)

    state = {
        'piles': {'deck': [_entry(c, False) for c in deck_codes]},
        'meta': {
            'created_kind': kind,
            'created_seed': args.seed,
            'created_top': args.top if kind == 'sistebbins' else None,
        },
    }
    put_rng(state, rng)
    save_state(state)
    print(f"new: created pile 'deck' ({kind}, n=52, seed={args.seed}). Top card: {cards.pretty(deck_codes[0])}")


def cmd_shuffle(args):
    state = require_state()
    entries = _pile(state, args.pile)
    if not entries:
        print(f"shuffle: pile '{args.pile}' is empty or doesn't exist.")
        return
    rng = get_rng(state)
    rng.shuffle(entries)
    put_rng(state, rng)
    save_state(state)
    print(f"shuffle: fully shuffled pile '{args.pile}' (n={len(entries)}).")


def cmd_cut(args):
    state = require_state()
    entries = _pile(state, args.pile)
    if not entries:
        print(f"cut: pile '{args.pile}' is empty or doesn't exist.")
        return
    rng = get_rng(state)
    n = args.n if args.n is not None else rng.randint(10, 40)
    n_eff = n % len(entries)
    codes = _codes(entries)
    new_codes = cards.cut(codes, n_eff)
    state['piles'][args.pile] = _reorder(entries, new_codes)
    put_rng(state, rng)
    save_state(state)
    print(f"cut: moved {n_eff} card(s) from top of '{args.pile}' to the bottom (n={n}).")


def cmd_dealoff(args):
    _deal_reversed(args.from_pile, args.to_pile, args.n, faceup=False, label='dealoff')


def cmd_deal(args):
    _deal_reversed(args.from_pile, args.to_pile, args.n, faceup=args.faceup, label='deal')


def _deal_reversed(from_name, to_name, n, faceup, label):
    state = require_state()
    src = _pile(state, from_name)
    if n < 0 or len(src) < n:
        print(f"{label}: n must be between 0 and {len(src)}; got {n}.")
        return
    taken = src[:n]
    rest = src[n:]
    dealt_reversed = [_entry(e['c'], faceup) for e in reversed(taken)]
    dest = _pile(state, to_name)
    state['piles'][to_name] = dealt_reversed + dest
    state['piles'][from_name] = rest
    save_state(state)
    face = 'face up' if faceup else 'face down'
    print(f"{label}: dealt {n} card(s) {face} from '{from_name}' onto '{to_name}' (order reversed).")


def cmd_top(args):
    state = require_state()
    entries = _pile(state, args.pile)
    n = min(args.n, len(entries))
    shown = entries[:n]
    print(f"top (PEEK) of '{args.pile}', {n} card(s) from the top:")
    print(' '.join(_mark(e) for e in shown))


def cmd_bottom(args):
    state = require_state()
    entries = _pile(state, args.pile)
    n = min(args.n, len(entries))
    shown = entries[len(entries) - n:]
    print(f"bottom (PEEK) of '{args.pile}', {n} card(s), nearest-bottom last:")
    print(' '.join(_mark(e) for e in shown))


def _mark(e):
    return cards.pretty(e['c']) + ('*' if e['up'] else '')


def cmd_place(args):
    state = require_state()
    code = cards.parse_card(args.card)
    if code is None:
        print(f"place: could not parse card from {args.card!r}.")
        return
    src_name, idx = _find_card(state, code)
    if src_name is None:
        print(f"place: {cards.pretty(code)} is not on the table.")
        return
    entry = state['piles'][src_name].pop(idx)
    entry['up'] = bool(args.faceup)
    dest = _pile(state, args.pile)
    dest.insert(0, entry)
    save_state(state)
    face = 'face up' if args.faceup else 'face down'
    print(f"place: moved {cards.pretty(code)} from '{src_name}' to top of '{args.pile}' ({face}).")


def cmd_drop(args):
    state = require_state()
    if args.from_pile not in state.get('piles', {}):
        print(f"drop: pile '{args.from_pile}' doesn't exist.")
        return
    from_entries = state['piles'].pop(args.from_pile)
    onto = _pile(state, args.onto)
    state['piles'][args.onto] = from_entries + onto
    save_state(state)
    print(f"drop: placed all {len(from_entries)} card(s) of '{args.from_pile}' on top of '{args.onto}'; '{args.from_pile}' removed.")


def cmd_flip(args):
    state = require_state()
    entries = _pile(state, args.pile)
    if not entries:
        print(f"flip: pile '{args.pile}' is empty or doesn't exist.")
        return
    state['piles'][args.pile] = [_entry(e['c'], not e['up']) for e in reversed(entries)]
    save_state(state)
    print(f"flip: turned pile '{args.pile}' over as a unit (n={len(entries)}).")


def cmd_riffle(args):
    state = require_state()
    if args.a == args.b:
        print("riffle: a and b must be two different piles.")
        return
    entries_a = _pile(state, args.a)
    entries_b = _pile(state, args.b)
    if not entries_a or not entries_b:
        print(f"riffle: both piles must have cards ('{args.a}'={len(entries_a)}, '{args.b}'={len(entries_b)}).")
        return
    rng = get_rng(state)
    codes_a = _codes(entries_a)
    codes_b = _codes(entries_b)
    new_codes = cards.riffle(codes_a, codes_b, rng=rng, max_run=args.max_run)
    lookup = {e['c']: e for e in entries_a + entries_b}
    new_entries = [lookup[c] for c in new_codes]

    if args.a != args.into:
        state['piles'].pop(args.a, None)
    if args.b != args.into and args.b != args.a:
        state['piles'].pop(args.b, None)
    state['piles'][args.into] = new_entries
    put_rng(state, rng)
    save_state(state)
    print(f"riffle: merged '{args.a}' ({len(codes_a)}) and '{args.b}' ({len(codes_b)}) into '{args.into}' (n={len(new_entries)}, max_run={args.max_run}).")


def cmd_spread(args):
    state = require_state()
    entries = _pile(state, args.pile)
    print(f"spread (PEEK) of '{args.pile}', top->bottom:")
    for i, e in enumerate(entries):
        mark = '*' if e['up'] else ''
        print(f"  {i:3d}  {cards.pretty(e['c']):>4s}{mark}")


def cmd_neighbors(args):
    state = require_state()
    code = cards.parse_card(args.card)
    if code is None:
        print(f"neighbors: could not parse card from {args.card!r}.")
        return
    entries = _pile(state, args.pile)
    idx = next((i for i, e in enumerate(entries) if e['c'] == code), None)
    if idx is None:
        print(f"neighbors: {cards.pretty(code)} not found in pile '{args.pile}'.")
        return
    above = cards.pretty(entries[idx - 1]['c']) if idx - 1 >= 0 else '(none -- it is the top card)'
    below = cards.pretty(entries[idx + 1]['c']) if idx + 1 < len(entries) else '(none -- it is the bottom card)'
    print(f"neighbors (PEEK) of {cards.pretty(code)} in '{args.pile}' (index {idx}): above={above}  below={below}")


def cmd_groups(args):
    state = require_state()
    entries = _pile(state, args.pile)
    codes = _codes(entries)
    groups = cards.deal_into_groups(codes, args.size)
    print(f"groups (PEEK) of '{args.pile}', size={args.size}:")
    if args.size > 4:
        print("  (note: suits_distinct is only meaningful/achievable for size<=4; with only 4")
        print("   suits to go around, larger groups are guaranteed to repeat a suit.)")
    if args.size > 13:
        print("  (note: ranks_distinct is only meaningful/achievable for size<=13.)")
    for i, g in enumerate(groups):
        suits_distinct = len({cards.suit(c) for c in g}) == len(g)
        ranks_distinct = len({cards.rank(c) for c in g}) == len(g)
        print(f"  group {i:3d}: {cards.pretty_list(g):<40s} suits_distinct={suits_distinct} ranks_distinct={ranks_distinct}")
    overall_suits = cards.groups_all_distinct(codes, args.size, cards.suit)
    overall_ranks = cards.groups_all_distinct(codes, args.size, cards.rank)
    print(f"  all groups suits_distinct={overall_suits}  all groups ranks_distinct={overall_ranks}")


def cmd_state(args):
    state = load_state()
    if state is None:
        print("No table state yet. Run 'new' first.")
        return
    piles = state.get('piles', {})
    total = sum(len(v) for v in piles.values())
    print("state: (counts only -- not a peek)")
    for name, entries in piles.items():
        print(f"  {name}: {len(entries)} card(s)")
    print(f"  TOTAL: {total} card(s) across {len(piles)} pile(s)")
    meta = state.get('meta')
    if meta:
        print(f"  created via: kind={meta.get('created_kind')} seed={meta.get('created_seed')} top={meta.get('created_top')}")


# --------------------------------------------------------------------------
# Argument parsing
# --------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(prog='sim/deck.py', description='Physical table simulator for card magic testing.')
    sub = p.add_subparsers(dest='command', required=True)

    sp = sub.add_parser('new', help="create pile 'deck'")
    sp.add_argument('kind', nargs='?', choices=['sistebbins', 'random', 'alt', 'redblack', 'newdeck'], default='newdeck')
    sp.add_argument('--seed', type=int, default=None)
    sp.add_argument('--top', default='AC')
    sp.set_defaults(func=cmd_new)

    sp = sub.add_parser('shuffle', help='full random shuffle of a pile')
    sp.add_argument('pile')
    sp.set_defaults(func=cmd_shuffle)

    sp = sub.add_parser('cut', help='cut n from top to bottom')
    sp.add_argument('pile')
    sp.add_argument('n', nargs='?', type=int, default=None)
    sp.set_defaults(func=cmd_cut)

    sp = sub.add_parser('dealoff', help='deal n cards from top of one pile onto another, reversing')
    sp.add_argument('from_pile', metavar='from')
    sp.add_argument('to_pile', metavar='to')
    sp.add_argument('n', type=int)
    sp.set_defaults(func=cmd_dealoff)

    sp = sub.add_parser('riffle', help='riffle two piles into a new one')
    sp.add_argument('a')
    sp.add_argument('b')
    sp.add_argument('into')
    sp.add_argument('--max-run', type=int, default=4)
    sp.set_defaults(func=cmd_riffle)

    sp = sub.add_parser('top', help='PEEK: show top n cards')
    sp.add_argument('pile')
    sp.add_argument('n', nargs='?', type=int, default=1)
    sp.set_defaults(func=cmd_top)

    sp = sub.add_parser('bottom', help='PEEK: show bottom n cards')
    sp.add_argument('pile')
    sp.add_argument('n', nargs='?', type=int, default=1)
    sp.set_defaults(func=cmd_bottom)

    sp = sub.add_parser('deal', help='deal n cards from top of one pile onto another, reversing')
    sp.add_argument('from_pile', metavar='from')
    sp.add_argument('to_pile', metavar='to')
    sp.add_argument('n', type=int)
    sp.add_argument('--faceup', action='store_true')
    sp.set_defaults(func=cmd_deal)

    sp = sub.add_parser('place', help='move a specific card (from anywhere) to the top of a pile')
    sp.add_argument('card')
    sp.add_argument('pile')
    sp.add_argument('--faceup', action='store_true')
    sp.set_defaults(func=cmd_place)

    sp = sub.add_parser('drop', help='put a whole pile on top of another, deleting the source')
    sp.add_argument('from_pile', metavar='from')
    sp.add_argument('onto')
    sp.set_defaults(func=cmd_drop)

    sp = sub.add_parser('flip', help='turn a whole pile face over')
    sp.add_argument('pile')
    sp.set_defaults(func=cmd_flip)

    sp = sub.add_parser('spread', help='PEEK: print all cards top->bottom')
    sp.add_argument('pile')
    sp.set_defaults(func=cmd_spread)

    sp = sub.add_parser('neighbors', help='PEEK: print the cards above/below a given card')
    sp.add_argument('card')
    sp.add_argument('pile')
    sp.set_defaults(func=cmd_neighbors)

    sp = sub.add_parser('groups', help='PEEK: print consecutive groups from the top')
    sp.add_argument('pile')
    sp.add_argument('size', type=int)
    sp.set_defaults(func=cmd_groups)

    sp = sub.add_parser('state', help='summary of piles and counts (not a peek)')
    sp.set_defaults(func=cmd_state)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == '__main__':
    main()
