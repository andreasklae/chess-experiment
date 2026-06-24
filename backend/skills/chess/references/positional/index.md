# Positional — Index

**Assess the position.** Read here to understand the *strengths, weaknesses,
and potentials* on the board — for BOTH sides — and turn them into a plan. This
is the layer between "no tactic is forcing me" and "make a plan": first see what
the position *is*, then decide what to do.

Your tools (`chess__show_position`, `chess__imagine_move`) name the concrete
features on the board and point here; this folder explains **what each feature
means and how to handle it**.

## Pages

| Read this when… | Page |
|---|---|
| you need the whole method — list both sides' strengths/weaknesses and decide what to do | [evaluate-position](evaluate-position.md) |
| there are pawn-structure weaknesses (isolated, doubled, backward, holes, hanging pawns) | [pawn-weaknesses](pawn-weaknesses.md) |
| there are pawn-structure strengths (passed pawn, connected pawns, majority, chains) | [pawn-strengths](pawn-strengths.md) |
| it's about where the pieces belong (open files, outposts, good/bad bishop, bishop pair, space) | [piece-activity](piece-activity.md) |
| you're converting a small edge — stop their plan (prophylaxis), blockade a passed/isolated pawn, seize the 7th rank | [prophylaxis-and-blockade](prophylaxis-and-blockade.md) |
| a king looks exposed/unsafe — yours or theirs | [king-safety](king-safety.md) |

## Routing

- A specific piece is attacked / there's a threat to answer → [`../strategy/handle-a-threat`](../strategy/handle-a-threat.md).
- A concrete tactic (fork, pin, loose piece) is in the air → [`../tactics/`](tactics/index.md).
- You've assessed it and need to commit to a plan → [`../strategy/make-a-plan`](../strategy/make-a-plan.md).
- You're clearly winning and converting → [`../strategy/convert-advantage`](../strategy/convert-advantage.md).
- It's the opening and you're developing → [`../principles/opening-principles`](../principles/opening-principles.md).
