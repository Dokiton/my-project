import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import settings

# Тесттер кестелерді өшіріп-қайта жасайды -> тек
# бөлек тест-дерекқорда: quizai -> quizai_test
if not settings.database_url.endswith("_test"):
    settings.database_url += "_test"

import app.models  # noqa: E402,F401
from app.core.database import Base, engine  # noqa: E402
from app.core.dependencies import get_keycloak_verifier  # noqa: E402
from app.core.security import KeycloakVerifier  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest.fixture(autouse=True)
def clean_state():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture(scope="session")
def rsa_test_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


@pytest.fixture
def auth_headers(rsa_test_keys):
    """Тест пайдаланушысы үшін RS256 Bearer токенін жасайтын фикстура."""
    private_key, public_key = rsa_test_keys
    verifier = KeycloakVerifier(
        issuer=settings.keycloak_issuer,
        jwks_url=settings.keycloak_jwks_url,
        audience=settings.KEYCLOAK_AUDIENCE,
    )
    verifier._jwks.get_signing_key_from_jwt = lambda _token: SimpleNamespace(
        key=public_key
    )
    app.dependency_overrides[get_keycloak_verifier] = lambda: verifier

    def _make_headers(user: User) -> dict[str, str]:
        now = int(time.time())
        claims = {
            "sub": user.keycloak_id,
            "iss": settings.keycloak_issuer,
            "aud": settings.KEYCLOAK_AUDIENCE,
            "iat": now,
            "exp": now + 300,
            "email": user.email,
            "name": user.full_name,
            "realm_access": {"roles": [user.role]},
        }
        token = jwt.encode(claims, private_key, algorithm="RS256")
        return {"Authorization": f"Bearer {token}"}

    try:
        yield _make_headers
    finally:
        app.dependency_overrides.pop(get_keycloak_verifier, None)
