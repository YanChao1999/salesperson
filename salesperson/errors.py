class PlatformError(Exception):
    """Base platform error."""


class PlatformNotFoundError(PlatformError, KeyError):
    pass


class AuthError(PlatformError):
    pass


class QuotaExceededError(PlatformError):
    pass


class PlanError(PlatformError):
    pass


class ProviderError(PlatformError):
    pass
