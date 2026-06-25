# Lichess puzzle themes — official definitions

Source: https://github.com/lichess-org/lila (translation/source/puzzleTheme.xml)
License: lichess.org is AGPL open-source; these strings are free content.
Retrieved 2026-06-25. These are the authoritative one-line definitions Lichess
uses to tag puzzles — the same theme tags our puzzle benchmark selects on. Used
to sharpen the wiki tactic-page descriptions and triggers (the agent's corpus).

---

## Fork (`fork`)
A move where the moved piece attacks two opponent pieces at once.

## Pin (`pin`)
A tactic involving pins, where a piece is unable to move without revealing an attack on a higher value piece.

## Skewer (`skewer`)
A motif involving a high value piece being attacked, moving out the way, and allowing a lower value piece behind it to be captured or attacked, the inverse of a pin.

## Discovered attack (`discoveredAttack`)
Moving a piece (such as a knight), that previously blocked an attack by a long range piece (such as a rook), out of the way of that piece.

## Double check (`doubleCheck`)
Checking with two pieces at once, as a result of a discovered attack where both the moving piece and the unveiled piece attack the opponent's king.

## Deflection (`deflection`)
A move that distracts an opposing piece from another duty that it performs, such as guarding a key square. Sometimes also called "overloading".

## Attraction (`attraction`)
An exchange or sacrifice encouraging or forcing an opponent piece to a square that allows a follow-up tactic.

## Interference (`interference`)
Moving a piece between two opponent pieces to leave one or both opponent pieces undefended, such as a knight on a defended square between two rooks.

## Clearance (`clearance`)
A move, often with tempo, that clears a square, file or diagonal for a follow-up tactical idea.

## Capture the defender (`capturingDefender`)
Removing a piece that is critical to defence of another piece, allowing the now undefended piece to be captured on a following move.

## Intermezzo (`intermezzo`)
Instead of playing the expected move, first interpose another move posing an immediate threat that the opponent must answer. Also known as "Zwischenzug" or "In between".

## Hanging piece (`hangingPiece`)
A tactic involving an opponent piece being undefended or insufficiently defended and free to capture.

## Sacrifice (`sacrifice`)
A tactic involving giving up material in the short-term, to gain an advantage again after a forced sequence of moves.

## Quiet move (`quietMove`)
A move that does not check, capture, or create an immediate threat to capture. Instead, it prepares a hidden and unavoidable threat for a later move.

## Defensive move (`defensiveMove`)
A precise move or sequence of moves that is needed to avoid losing material or another advantage.

## Advanced pawn (`advancedPawn`)
One of your pawns is deep into the opponent position, maybe threatening to promote.

## Promotion (`promotion`)
Promote one of your pawn to a queen or minor piece.

## Exposed king (`exposedKing`)
A tactic involving a king with few defenders around it, often leading to checkmate.

## Back rank mate (`backRankMate`)
Checkmate the king on the home rank, when it is trapped there by its own pieces.

## Smothered mate (`smotheredMate`)
A checkmate delivered by a knight in which the mated king is unable to move because it is surrounded (or smothered) by its own pieces.

## Trapped piece (`trappedPiece`)
A piece is unable to escape capture as it has limited moves.

## Zugzwang (`zugzwang`)
The opponent is limited in the moves they can make, and all moves worsen their position.

## X-Ray attack (`xRayAttack`)
A piece attacks or defends a square, through an enemy piece.

## Discovered check (`discoveredCheck`)
Move a piece to reveal a check from a hidden attacking piece, which often leads to a decisive advantage.

## Double bishop mate (`doubleBishopMate`)
Two attacking bishops on adjacent diagonals deliver mate to a king obstructed by friendly pieces.
