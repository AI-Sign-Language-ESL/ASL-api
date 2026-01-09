from rest_framework_simplejwt.tokens import RefreshToken


def generate_access_token(user):
    """
    Generates a standard SimpleJWT access token.
    Compatible with IsAuthenticated permission.
    """
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)


def generate_refresh_token(user):
    """
    Generates a standard SimpleJWT refresh token.
    """
    refresh = RefreshToken.for_user(user)
    return str(refresh)
