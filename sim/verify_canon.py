#!/usr/bin/env python3
"""sim/verify_canon.py -- Monte Carlo verification of three self-working
card-magic procedures, built on top of workspace/cards.py:

  A. Gilbreath principle on a Si Stebbins stack (suits-of-4 / ranks-of-13).
  B. "Gemini Twins" mate-prediction effect.
  C. The "cut-deeper" force.

Every trial is generated from a single seeded master RNG (see MASTER_SEED
below) so this whole report is exactly reproducible.

Run: python3 sim/verify_canon.py
"""

from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'workspace'))
import cards  # noqa: E402

MASTER_SEED = 20260916
MAX_RUNS = (2, 3, 4, 6)
BASE_SUIT_CYCLE = 'CHSD'


def pct(num, den):
    return 0.0 if den == 0 else 100.0 * num / den


# ==========================================================================
# A. Gilbreath principle on a Si Stebbins stack
# ==========================================================================

def run_part_a(rng, trials=3000):
    print("=" * 78)
    print("A. GILBREATH PRINCIPLE ON A SI STEBBINS STACK")
    print("=" * 78)
    print(f"trials={trials}  (random top card, random suit-cycle rotation,")
    print("50% chance of a random pre-cut, deal-off n in [8,44], one riffle")
    print(f"with max_run in {MAX_RUNS})")
    print()

    main_stats = {}      # (precut, max_run) -> [n, a_pass, b_pass]
    ctrl1_stats = {}      # no-reversal control (plain cut split, no deal-off)
    ctrl2_stats = {}      # two-riffles control

    def bump(table, key, a_ok, b_ok):
        row = table.setdefault(key, [0, 0, 0])
        row[0] += 1
        row[1] += int(a_ok)
        row[2] += int(b_ok)

    for _ in range(trials):
        top = rng.choice(cards.FULL_DECK)
        rotation = rng.randrange(4)
        suits_cycle = BASE_SUIT_CYCLE[rotation:] + BASE_SUIT_CYCLE[:rotation]
        deck = cards.si_stebbins(top=top, step=3, suits=suits_cycle)

        precut = rng.random() < 0.5
        if precut:
            c = rng.randint(1, 51)
            deck = cards.cut(deck, c)

        n = rng.randint(8, 44)
        max_run = rng.choice(MAX_RUNS)
        key = (precut, max_run)

        # --- MAIN procedure: deal off n (reverses), single riffle ---
        p, rest = cards.deal_off(deck, n)
        merged = cards.riffle(rest, p, rng=rng, max_run=max_run)
        rep = cards.gilbreath_report(merged)
        bump(main_stats, key, rep['suits4_ok'], rep['ranks13_ok'])

        # --- CONTROL 1: split by a plain cut, no deal-off reversal ---
        packet1 = deck[:n]           # natural order, NOT reversed
        packet2 = deck[n:]
        merged_c1 = cards.riffle(packet1, packet2, rng=rng, max_run=max_run)
        rep_c1 = cards.gilbreath_report(merged_c1)
        bump(ctrl1_stats, key, rep_c1['suits4_ok'], rep_c1['ranks13_ok'])

        # --- CONTROL 2: take the properly-merged deck and riffle it AGAIN ---
        m = rng.randint(1, 51)
        merged_c2 = cards.riffle(merged[:m], merged[m:], rng=rng, max_run=max_run)
        rep_c2 = cards.gilbreath_report(merged_c2)
        bump(ctrl2_stats, key, rep_c2['suits4_ok'], rep_c2['ranks13_ok'])

    def print_table(title, table):
        print(f"-- {title} --")
        print(f"  {'precut':<7} {'max_run':<8} {'n':>5} {'suits4-ok%':>11} {'ranks13-ok%':>12}")
        tot = [0, 0, 0]
        for precut in (False, True):
            for mr in MAX_RUNS:
                row = table.get((precut, mr), [0, 0, 0])
                n, a_ok, b_ok = row
                tot[0] += n
                tot[1] += a_ok
                tot[2] += b_ok
                print(f"  {str(precut):<7} {mr:<8} {n:>5} {pct(a_ok, n):>10.2f}% {pct(b_ok, n):>11.2f}%")
        print(f"  {'ALL':<7} {'':<8} {tot[0]:>5} {pct(tot[1], tot[0]):>10.2f}% {pct(tot[2], tot[0]):>11.2f}%")
        print()

    print_table("MAIN (deal-off reversal + one riffle)", main_stats)
    print_table("CONTROL 1: plain cut split, NO deal-off reversal, one riffle", ctrl1_stats)
    print_table("CONTROL 2: proper deal-off + riffle, THEN a second cut+riffle", ctrl2_stats)


# ==========================================================================
# B. Gemini Twins
# ==========================================================================

def run_part_b(rng, trials=5000):
    print("=" * 78)
    print("B. GEMINI TWINS (mate prediction)")
    print("=" * 78)
    print(f"trials={trials}")
    print()

    skip_count = 0
    valid = 0
    p1_above_b = 0
    p1_below_b = 0
    p2_above_t = 0
    p2_below_t = 0

    # variant: k2 allowed to exceed (cards above P1 - 1), segmented by
    # whether it actually did exceed or not.
    variant_safe = [0, 0]   # [n, p1_above_b_hits] when k2v stayed within the safe cap
    variant_over = [0, 0]   # [n, p1_above_b_hits] when k2v exceeded the safe cap
    variant_over_p1_disturbed = 0  # count where P1 itself got swept into the dealt packet

    for _ in range(trials):
        deck = list(cards.FULL_DECK)
        rng.shuffle(deck)
        t = deck[0]
        b = deck[-1]
        P1 = cards.mate(b)
        P2 = cards.mate(t)

        if P1 == t or P2 == b:
            skip_count += 1
            continue
        valid += 1

        deck50 = [c for c in deck if c != P1 and c != P2]

        # Phase 1
        k1 = rng.randint(3, 30)
        dealt1_rev, remaining = cards.deal_off(deck50, k1)
        phase1 = remaining + [P1] + dealt1_rev
        idx1 = phase1.index(P1)  # number of cards above P1

        # Phase 2 (proper: k2 stays strictly above P1)
        k2_cap = max(3, min(15, idx1 - 1))
        k2 = rng.randint(3, k2_cap)
        dealt2_rev, remaining2 = cards.deal_off(phase1, k2)
        final_deck = remaining2 + [P2] + dealt2_rev

        i1 = final_deck.index(P1)
        i2 = final_deck.index(P2)
        above1 = final_deck[i1 - 1] if i1 > 0 else None
        below1 = final_deck[i1 + 1] if i1 + 1 < len(final_deck) else None
        above2 = final_deck[i2 - 1] if i2 > 0 else None
        below2 = final_deck[i2 + 1] if i2 + 1 < len(final_deck) else None

        if above1 == b:
            p1_above_b += 1
        if below1 == b:
            p1_below_b += 1
        if above2 == t:
            p2_above_t += 1
        if below2 == t:
            p2_below_t += 1

        # Variant: k2 chosen without regard to the "above P1" cap.
        k2v = rng.randint(3, 30)
        dealt2v_rev, remaining2v = cards.deal_off(phase1, k2v)
        final_deck_v = remaining2v + [P2] + dealt2v_rev
        i1v = final_deck_v.index(P1)
        above1v = final_deck_v[i1v - 1] if i1v > 0 else None
        hit = int(above1v == b)
        if k2v <= idx1 - 1:
            variant_safe[0] += 1
            variant_safe[1] += hit
        else:
            variant_over[0] += 1
            variant_over[1] += hit
            if k2v > idx1:
                variant_over_p1_disturbed += 1

    print(f"skip rate (P1==t or P2==b, degenerate setup): {skip_count}/{trials} = {pct(skip_count, trials):.2f}%")
    print(f"valid trials analyzed: {valid}")
    print()
    print("Standard procedure (k2 kept strictly above P1):")
    print(f"  P1 : card ABOVE P1 == b : {p1_above_b}/{valid} = {pct(p1_above_b, valid):.3f}%")
    print(f"  P1 : card BELOW P1 == b : {p1_below_b}/{valid} = {pct(p1_below_b, valid):.3f}%   (control -- should be ~chance)")
    print(f"  P2 : card ABOVE P2 == t : {p2_above_t}/{valid} = {pct(p2_above_t, valid):.3f}%")
    print(f"  P2 : card BELOW P2 == t : {p2_below_t}/{valid} = {pct(p2_below_t, valid):.3f}%   (control -- should be ~chance)")
    print()
    print("Variant: k2 drawn from [3,30] with NO regard to cards-above-P1 cap:")
    print(f"  k2 stayed within safe cap : n={variant_safe[0]:5d}  P1-above==b rate = {pct(variant_safe[1], variant_safe[0]):.3f}%")
    print(f"  k2 exceeded safe cap      : n={variant_over[0]:5d}  P1-above==b rate = {pct(variant_over[1], variant_over[0]):.3f}%")
    print(f"    of which k2v actually dealt PAST P1 itself (swept it into the packet): {variant_over_p1_disturbed}/{variant_over[0]}")
    print("  -> when k2 is allowed past the cap, the prediction still works whenever it")
    print("     happens not to reach P1, but once k2 deals P1 itself into the packet the")
    print("     'above P1 == b' relationship collapses to chance.")
    print()


# ==========================================================================
# C. Cut-deeper force
# ==========================================================================

def _flip_as_unit(entries):
    """Reverse a list of [card, face_up] pairs and toggle every face flag."""
    return [[card, not up] for card, up in reversed(entries)]


def _cut_deeper_trial(deck, a, c):
    """Run the two-cut-and-flip procedure; return (X, deck_after) where X is
    the first face-down card found spreading from the top."""
    entries = [[card, False] for card in deck]
    entries = _flip_as_unit(entries[:a]) + entries[a:]
    entries = _flip_as_unit(entries[:c]) + entries[c:]
    X = next((card for card, up in entries if not up), None)
    return X, entries


def run_part_c(rng, trials=5000):
    print("=" * 78)
    print("C. CUT-DEEPER FORCE")
    print("=" * 78)
    print(f"trials={trials}  (a uniform 3-20, c uniform a+1..45)")
    print()

    hits = 0
    for _ in range(trials):
        deck = list(cards.FULL_DECK)
        rng.shuffle(deck)
        T = deck[0]
        a = rng.randint(3, 20)
        c = rng.randint(a + 1, 45)
        X, _ = _cut_deeper_trial(deck, a, c)
        if X == T:
            hits += 1
    print(f"MAIN (c > a, deeper second cut): X == T in {hits}/{trials} = {pct(hits, trials):.4f}%")
    print()

    # Failure mode: c <= a.
    eq_trials = min(2000, trials)
    hits_eq = 0
    top_face_down_eq = 0
    for _ in range(eq_trials):
        deck = list(cards.FULL_DECK)
        rng.shuffle(deck)
        T = deck[0]
        a = rng.randint(3, 20)
        c = a  # equal cut sizes
        X, entries = _cut_deeper_trial(deck, a, c)
        if X == T:
            hits_eq += 1
        if not entries[0][1]:
            top_face_down_eq += 1
    print(f"c == a (second cut same size as first): X == T in {hits_eq}/{eq_trials} = {pct(hits_eq, eq_trials):.4f}%")
    print(f"  (degenerate: the two flips cancel out -- deck is fully restored, face down,")
    print(f"   top card face-down immediately in {top_face_down_eq}/{eq_trials} trials, so there is")
    print(f"   no visible face-up block at all; the 'force' has no presentation left to give.)")
    print()

    lt_trials = min(2000, trials)
    hits_lt = 0
    top_face_down_lt = 0
    for _ in range(lt_trials):
        deck = list(cards.FULL_DECK)
        rng.shuffle(deck)
        T = deck[0]
        a = rng.randint(4, 20)
        c = rng.randint(1, a - 1)  # smaller second cut
        X, entries = _cut_deeper_trial(deck, a, c)
        if X == T:
            hits_lt += 1
        if not entries[0][1]:
            top_face_down_lt += 1
    print(f"c < a (second cut SMALLER than first): X == T in {hits_lt}/{lt_trials} = {pct(hits_lt, lt_trials):.4f}%")
    print(f"  (failure mode: the resulting top card is ALREADY face-down in")
    print(f"   {top_face_down_lt}/{lt_trials} trials -- there is no leading face-up block to spread")
    print(f"   past at all, so 'the first face-down card' is just the new top card, which is")
    print(f"   essentially a random card, not T. The premise of the force silently breaks.)")
    print()


def main():
    print(f"verify_canon.py -- MASTER_SEED={MASTER_SEED}")
    print()
    rng = random.Random(MASTER_SEED)
    run_part_a(rng)
    run_part_b(rng)
    run_part_c(rng)
    print("=" * 78)
    print("DONE")


if __name__ == '__main__':
    main()
