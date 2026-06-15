# Mating Patterns — Index

Checkmating patterns and the nets that lead to them: back-rank mate,
smothered mate, the ladder/box mate (two rooks or Q+R), K+Q vs K, K+R vs K,
and the common piece-coordination mates against an exposed king.

**Read a page here when:** the enemy king's escape squares are few (watch
the **King mvt** column in `list_legal_moves` and the **Enemy king
mobility** line in `imagine_move`), the king is on the back rank or cornered,
or you have a material edge and want to convert by mating rather than
grinding.

**Choose the simplest mate available.** With two major pieces the ladder is
fully forced — look no further. With a lone queen or rook plus king, use the
basic technique page. Only hunt fancier mates when no simple one exists;
often the fastest "mate" is to promote a pawn first and then mate with the
queen ([[strategic-thinking/convert-advantage]]).

## Pages

| Page | When it applies | Read with |
|------|-----------------|-----------|
| ladder-mate | You have two rooks / queen+rook vs a king in the open — the simplest forced mate (drill) | `read_reference(skill_name="chess", path="patterns/mating-patterns/ladder-mate.md")` |
| king-queen-mate | King + queen vs bare king (e.g. right after promoting) — drill | `read_reference(skill_name="chess", path="patterns/mating-patterns/king-queen-mate.md")` |
| king-rook-mate | King + rook vs bare king — drill | `read_reference(skill_name="chess", path="patterns/mating-patterns/king-rook-mate.md")` |
| back-rank-mate | Enemy king on its back rank, escape squares blocked by its own pawns, you have a rook/queen that can check along the rank | `read_reference(skill_name="chess", path="patterns/mating-patterns/back-rank-mate.md")` |
| smothered-mate | Enemy king cornered behind its own pieces; you have a knight (Q+N: the forced Philidor sequence) | `read_reference(skill_name="chess", path="patterns/mating-patterns/smothered-mate.md")` |
| anastasia-mate | Enemy king on the edge file; your knight can reach the e7-type square; rook free for the edge file | `read_reference(skill_name="chess", path="patterns/mating-patterns/anastasia-mate.md")` |
| arabian-mate | Enemy king cornered; you have rook + knight | `read_reference(skill_name="chess", path="patterns/mating-patterns/arabian-mate.md")` |
| hook-mate | Enemy king on the edge; rook + knight + pawn on that wing | `read_reference(skill_name="chess", path="patterns/mating-patterns/hook-mate.md")` |
| greco-mate | Castled king, open/openable h-file, your bishop on the a2-g8 diagonal, queen available | `read_reference(skill_name="chess", path="patterns/mating-patterns/greco-mate.md")` |
| queen-contact-mates | Enemy king with 2+ escape squares blocked by its own pieces; queen can land adjacent (epaulette / dovetail / swallow's tail) | `read_reference(skill_name="chess", path="patterns/mating-patterns/queen-contact-mates.md")` |
| opera-mate | Uncastled enemy king on an openable central file; your rook + bishop coordinate | `read_reference(skill_name="chess", path="patterns/mating-patterns/opera-mate.md")` |
| blind-swine-mate | Both your rooks reach (or can reach) the enemy 7th rank against a castled king | `read_reference(skill_name="chess", path="patterns/mating-patterns/blind-swine-mate.md")` |

## Routing

- It's a tactic that wins material rather than a mate → [`../index.md`](../index.md).
- It's a basic K+Q / K+R technical mate in an endgame → also see [`../../endgames/`](../../endgames/index.md).
- **Always confirm the mate with `imagine_move`** (it flags `gives
  checkmate`) or by scanning `list_legal_moves` for the `checkmate` flag
  before committing.
