"""Typed exceptions raised by the chess.com driver."""


class ChessComDriverError(RuntimeError):
    """Base class for any error originating from the driver."""


class ChessComSetupError(ChessComDriverError):
    """Raised when the browser/page cannot be brought into a playable state.

    Examples: Cloudflare interstitial unresolved, login required, the
    /play/computer DOM does not match the expected layout, or the Engine
    bot group can't be opened.
    """


class ChessComGameError(ChessComDriverError):
    """Raised when in-game state is inconsistent with what the driver expects.

    Examples: chess.com refused a move we believed was legal, the bot did
    not respond within the timeout, the game ended unexpectedly.
    """


class ChessComMoveTimeout(ChessComGameError):
    """Raised when the chess.com bot does not move within the timeout."""


class ChessComIllegalMove(ChessComGameError):
    """Raised when chess.com rejects a move we tried to submit."""
