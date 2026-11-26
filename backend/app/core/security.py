from dataclasses import dataclass

import jwt

APP_ROLES = ("admin", "teacher", "student")


class AuthUnavailableError(Exception):
    """Keycloak JWKS қызметі қолжетімсіз болғанда туындайтын қате."""


@dataclass(frozen=True)
class Identity:
    """Keycloak JWT токенінен алынған пайдаланушы сәйкестендіру деректері."""

    keycloak_id: str
    email: str | None = None
    full_name: str | None = None
    role: str | None = None


class KeycloakVerifier:
    """Keycloak OIDC JWT токендерін JWKS ашық кілттері арқылы тексеру."""

    def __init__(self, issuer: str, jwks_url: str, audience: str) -> None:
        self.issuer = issuer
        self.audience = audience
        self._jwks = jwt.PyJWKClient(jwks_url, cache_keys=True)

    def verify(self, token: str) -> dict:
        """RS256 токенді тексеріп, claims сөздігін қайтару."""
        try:
            key = self._jwks.get_signing_key_from_jwt(token)
        except (jwt.PyJWKClientConnectionError, OSError) as exc:
            raise AuthUnavailableError("Keycloak қолжетімсіз") from exc
        return jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            issuer=self.issuer,
            audience=self.audience,
            options={"require": ["exp", "iat", "iss", "sub", "aud"]},
        )


def identity_from_claims(claims: dict) -> Identity:
    """JWT claims ішінен пайдаланушы мен ең жоғары рөлді шығарып алу."""
    roles = set(claims.get("realm_access", {}).get("roles", []))
    role = next((r for r in APP_ROLES if r in roles), None)
    return Identity(
        keycloak_id=claims["sub"],
        email=claims.get("email"),
        full_name=claims.get("name") or claims.get("preferred_username"),
        role=role,
    )
