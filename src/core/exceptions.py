"""Custom exception hierarchy for the F1 Facts API.

Every exception carries a human-readable *detail* message and a fixed
HTTP status code so the global exception handler in ``main.py`` can
translate it into a consistent JSON error response.
"""

from fastapi import status


# ── Base ─────────────────────────────────────────────────────────────────────
class F1FactsAPIError(Exception):
    """Base exception for all F1 Facts API errors.

    Subclasses set *status_code*; callers pass a descriptive *detail*.
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, detail: str = "An unexpected error occurred"):
        self.detail = detail
        super().__init__(detail)


# ── 400 Bad Request ──────────────────────────────────────────────────────────
class BadRequestError(F1FactsAPIError):
    """The request body or parameters are invalid or incomplete."""

    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail: str = "The request was invalid or incomplete"):
        super().__init__(detail)


class EmptyUpdateError(BadRequestError):
    """A PATCH/PUT request was sent with no updatable fields."""

    def __init__(self, resource: str = "resource"):
        super().__init__(
            f"No fields to update on {resource}. "
            "Please provide at least one field to change."
        )


class InvalidVoteError(BadRequestError):
    """The vote references a driver that is not part of the matchup."""

    def __init__(self):
        super().__init__(
            "The winner_id must be one of the two drivers in the matchup. "
            "Please supply a valid driver ID."
        )


# ── 401 Unauthorized ─────────────────────────────────────────────────────────
class UnauthorizedError(F1FactsAPIError):
    """Authentication is required or the supplied credentials are invalid."""

    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self, detail: str = "Authentication is required to access this resource"):
        super().__init__(detail)


class InvalidCredentialsError(UnauthorizedError):
    """The username/password combination is wrong."""

    def __init__(self):
        super().__init__(
            "Invalid username or password. "
            "Please check your credentials and try again."
        )


class InvalidTokenError(UnauthorizedError):
    """The JWT token is expired, malformed, or otherwise invalid."""

    def __init__(self):
        super().__init__(
            "Could not validate your authentication token. "
            "Please log in again to obtain a new token."
        )


class TokenRevokedError(UnauthorizedError):
    """The token has been revoked (e.g. after logout)."""

    def __init__(self):
        super().__init__(
            "This token has been revoked. "
            "Please log in again to obtain a new token."
        )


class InvalidRefreshTokenError(UnauthorizedError):
    """The refresh token is expired, invalid, or already revoked."""

    def __init__(self):
        super().__init__(
            "Invalid or expired refresh token. "
            "Please log in again."
        )


# ── 403 Forbidden ────────────────────────────────────────────────────────────
class ForbiddenError(F1FactsAPIError):
    """The authenticated user lacks the required permissions."""

    status_code = status.HTTP_403_FORBIDDEN

    def __init__(self, detail: str = "You do not have permission to perform this action"):
        super().__init__(detail)


class AdminRequiredError(ForbiddenError):
    """The endpoint requires administrator privileges."""

    def __init__(self):
        super().__init__(
            "This action requires administrator privileges. "
            "Please contact an admin if you believe this is an error."
        )


class InsufficientRoleError(ForbiddenError):
    """The user's role is below the minimum required for this endpoint."""

    def __init__(self, required_role: str):
        super().__init__(
            f"This action requires at least '{required_role}' role. "
            "Your current permissions are insufficient."
        )


# ── 404 Not Found ────────────────────────────────────────────────────────────
class NotFoundError(F1FactsAPIError):
    """The requested resource does not exist."""

    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, resource: str = "Resource", identifier: str | None = None):
        msg = f"{resource} not found"
        if identifier:
            msg = f"{resource} with ID '{identifier}' was not found"
        msg += ". Please verify the ID and try again."
        super().__init__(msg)


class UserNotFoundError(NotFoundError):
    def __init__(self, user_id: str | None = None):
        super().__init__("User", user_id)


class DriverNotFoundError(NotFoundError):
    def __init__(self, driver_id: str | None = None):
        super().__init__("Driver", driver_id)


class TeamNotFoundError(NotFoundError):
    def __init__(self, team_id: str | None = None):
        super().__init__("Team", team_id)


class FavouriteListNotFoundError(NotFoundError):
    def __init__(self, fav_id: str | None = None):
        super().__init__("Favourite list", fav_id)


class FactNotFoundError(NotFoundError):
    def __init__(self, fact_id: str | None = None):
        super().__init__("Fact", fact_id)


class HotTakeNotFoundError(NotFoundError):
    def __init__(self, take_id: str | None = None):
        super().__init__("Hot take", take_id)


class HotTakeDeleteNotFoundError(F1FactsAPIError):
    """The hot take doesn't exist or doesn't belong to the current user."""

    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, take_id: str | None = None):
        msg = "Hot take not found, or you are not the author."
        if take_id:
            msg = (
                f"Hot take with ID '{take_id}' was not found, "
                "or you are not the author. Only the original author "
                "(or an admin) can delete a hot take."
            )
        super().__init__(msg)


class PredictionNotFoundError(NotFoundError):
    def __init__(self, pred_id: str | None = None):
        super().__init__("Prediction", pred_id)


class RaceRoundNotFoundError(NotFoundError):
    """A calendar round number that doesn't exist in the 2025 season."""

    def __init__(self, round_number: int):
        super().__init__(
            resource="Race round",
            identifier=str(round_number),
        )


# ── 409 Conflict ─────────────────────────────────────────────────────────────
class ConflictError(F1FactsAPIError):
    """The request conflicts with the current state of the resource."""

    status_code = status.HTTP_409_CONFLICT

    def __init__(self, detail: str = "This action conflicts with existing data"):
        super().__init__(detail)


class UsernameAlreadyTakenError(ConflictError):
    def __init__(self, username: str | None = None):
        msg = "This username is already taken. Please choose a different username."
        if username:
            msg = (
                f"The username '{username}' is already taken. "
                "Please choose a different username."
            )
        super().__init__(msg)


class EmailAlreadyRegisteredError(ConflictError):
    def __init__(self, email: str | None = None):
        msg = "This email address is already registered."
        if email:
            msg = (
                f"The email '{email}' is already associated with an account. "
                "Please use a different email or log in to your existing account."
            )
        super().__init__(msg)


class DuplicateFavouriteItemError(ConflictError):
    def __init__(self, item_name: str | None = None):
        msg = "This item is already in the favourite list."
        if item_name:
            msg = (
                f"'{item_name}' is already in this favourite list. "
                "Each item can only appear once per list."
            )
        super().__init__(msg)


class DuplicatePredictionError(ConflictError):
    def __init__(self, category: str, season: int):
        super().__init__(
            f"You already have a '{category}' prediction for the {season} season. "
            "Update or delete your existing prediction instead of creating a new one."
        )
