import logging
import time
import uuid
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

import app.core.dependencies as deps
from app.core.config import Settings, settings
from app.core.database import engine
from app.core.security import (
    AuthUnavailableError,
    Identity,
    KeycloakVerifier,
    identity_from_claims,
)
from app.main import app
from app.models.user import User
from app.repositories.user_repository import UserRepository

ISSUER = "http://localhost:8080/realms/edu-realm"
JWKS_URL = f"{ISSUER}/protocol/openid-connect/certs"
AUDIENCE = "edu-api"

client = TestClient(app)
SessionTest = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="module")
def rsa_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key


def _make_verifier(public_key) -> KeycloakVerifier:
    verifier = KeycloakVerifier(issuer=ISSUER, jwks_url=JWKS_URL, audience=AUDIENCE)
    verifier._jwks.get_signing_key_from_jwt = lambda _token: SimpleNamespace(
        key=public_key
    )
    return verifier


def _base_claims(**overrides) -> dict:
    now = int(time.time())
    claims = {
        "sub": "kc-user-123",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + 300,
        "email": "student@demo.kz",
        "name": "Demo Student",
        "realm_access": {"roles": ["student", "offline_access"]},
    }
    claims.update(overrides)
    return claims


def test_verify_valid_rs256_token(rsa_keys):
    private_key, public_key = rsa_keys
    token = jwt.encode(_base_claims(), private_key, algorithm="RS256")
    verifier = _make_verifier(public_key)

    claims = verifier.verify(token)
    assert claims["sub"] == "kc-user-123"
    assert claims["iss"] == ISSUER
    assert claims["aud"] == AUDIENCE


def test_verify_rejects_hs256_and_none_algorithms(rsa_keys):
    _, public_key = rsa_keys
    verifier = _make_verifier(public_key)

    hs_token = jwt.encode(
        _base_claims(),
        "symmetric-secret-key-32-bytes-long",
        algorithm="HS256",
    )
    with pytest.raises(jwt.InvalidAlgorithmError):
        verifier.verify(hs_token)

    none_token = jwt.encode(_base_claims(), None, algorithm="none")
    with pytest.raises(jwt.PyJWTError):
        verifier.verify(none_token)


def test_verify_rejects_wrong_issuer_and_audience(rsa_keys):
    private_key, public_key = rsa_keys
    verifier = _make_verifier(public_key)

    wrong_iss = jwt.encode(
        _base_claims(iss="http://localhost:8080/realms/other"),
        private_key,
        algorithm="RS256",
    )
    with pytest.raises(jwt.InvalidIssuerError):
        verifier.verify(wrong_iss)

    wrong_aud = jwt.encode(
        _base_claims(aud="other-api"),
        private_key,
        algorithm="RS256",
    )
    with pytest.raises(jwt.InvalidAudienceError):
        verifier.verify(wrong_aud)


def test_verify_rejects_expired_and_missing_required_claims(rsa_keys):
    private_key, public_key = rsa_keys
    verifier = _make_verifier(public_key)

    expired = jwt.encode(
        _base_claims(exp=int(time.time()) - 10),
        private_key,
        algorithm="RS256",
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        verifier.verify(expired)

    claims_no_iat = _base_claims()
    del claims_no_iat["iat"]
    missing_iat = jwt.encode(claims_no_iat, private_key, algorithm="RS256")
    with pytest.raises(jwt.MissingRequiredClaimError):
        verifier.verify(missing_iat)


def test_identity_from_claims_role_precedence():
    admin_id = identity_from_claims(
        _base_claims(realm_access={"roles": ["student", "teacher", "admin"]})
    )
    assert admin_id == Identity(
        keycloak_id="kc-user-123",
        email="student@demo.kz",
        full_name="Demo Student",
        role="admin",
    )

    teacher_id = identity_from_claims(
        _base_claims(realm_access={"roles": ["student", "teacher"]})
    )
    assert teacher_id.role == "teacher"

    student_id = identity_from_claims(
        _base_claims(realm_access={"roles": ["offline_access", "student"]})
    )
    assert student_id.role == "student"

    no_role = identity_from_claims(
        {
            "sub": "kc-user-999",
            "preferred_username": "guest@demo.kz",
            "realm_access": {"roles": ["offline_access"]},
        }
    )
    assert no_role == Identity(
        keycloak_id="kc-user-999",
        email=None,
        full_name="guest@demo.kz",
        role=None,
    )


def test_user_repository_sync_lifecycle(monkeypatch):
    db: Session = SessionTest()
    try:
        repo = UserRepository(db)

        # 1. Жаңа пайдаланушы жасау
        kc_id = f"kc-{uuid.uuid4().hex[:12]}"
        email = f"sync_{uuid.uuid4().hex[:8]}@demo.kz"
        created = repo.sync(
            Identity(
                keycloak_id=kc_id,
                email=email,
                full_name="Initial Name",
                role="student",
            ),
            role="student",
        )
        assert created.keycloak_id == kc_id
        assert created.email == email
        assert created.role == "student"

        # 2. Өзгеріс жоқ кезде ДҚ-ға commit жасалмайды
        commits = []
        orig_commit = db.commit
        monkeypatch.setattr(db, "commit", lambda: commits.append(1))
        same = repo.sync(
            Identity(
                keycloak_id=kc_id,
                email=email,
                full_name="Initial Name",
                role="student",
            ),
            role="student",
        )
        assert same.id == created.id
        assert commits == []
        monkeypatch.setattr(db, "commit", orig_commit)

        # 3. Аты мен рөлі өзгерсе — жаңарту
        updated = repo.sync(
            Identity(
                keycloak_id=kc_id,
                email=email,
                full_name="Updated Teacher",
                role="teacher",
            ),
            role="teacher",
        )
        assert updated.id == created.id
        assert updated.full_name == "Updated Teacher"
        assert updated.role == "teacher"

        # 4. Legacy-жазбаны ('legacy-...') email бойынша бір рет байланыстыру
        legacy_email = f"legacy_{uuid.uuid4().hex[:8]}@demo.kz"
        legacy = repo.create(
            User(
                keycloak_id=f"legacy-{uuid.uuid4().hex[:8]}",
                email=legacy_email,
                full_name="Legacy User",
                role="student",
            )
        )
        new_kc_id = f"kc-new-{uuid.uuid4().hex[:8]}"
        linked = repo.sync(
            Identity(
                keycloak_id=new_kc_id,
                email=legacy_email,
                full_name="Legacy User",
                role="student",
            ),
            role="student",
        )
        assert linked.id == legacy.id
        assert linked.keycloak_id == new_kc_id
    finally:
        db.close()


def test_get_auth_me_with_bearer_token_and_sync(rsa_keys, caplog):
    private_key, public_key = rsa_keys
    verifier = _make_verifier(public_key)
    app.dependency_overrides[deps.get_keycloak_verifier] = lambda: verifier
    try:
        kc_id = f"kc-{uuid.uuid4().hex[:12]}"
        email = f"bearer_{uuid.uuid4().hex[:8]}@demo.kz"
        token = jwt.encode(
            _base_claims(
                sub=kc_id,
                email=email,
                name="Bearer Teacher",
                realm_access={"roles": ["teacher"]},
            ),
            private_key,
            algorithm="RS256",
        )

        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["keycloak_id"] == kc_id
        assert data["email"] == email
        assert data["full_name"] == "Bearer Teacher"
        assert data["role"] == "teacher"

        # Рөлі жоқ токен -> 403
        no_role_token = jwt.encode(
            _base_claims(sub="kc-norole", realm_access={"roles": ["offline_access"]}),
            private_key,
            algorithm="RS256",
        )
        res_no_role = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {no_role_token}"}
        )
        assert res_no_role.status_code == 403
        assert "қосымша рөлі берілмеген" in res_no_role.json()["detail"]

        # Қате аудитория -> 401 және логқа себебі жазылады (токеннің өзі емес)
        bad_aud_token = jwt.encode(
            _base_claims(aud="wrong-api"),
            private_key,
            algorithm="RS256",
        )
        with caplog.at_level(logging.WARNING, logger="app.core.dependencies"):
            res_bad = client.get(
                "/api/auth/me", headers={"Authorization": f"Bearer {bad_aud_token}"}
            )
        assert res_bad.status_code == 401
        assert "InvalidAudienceError" in caplog.text
        assert bad_aud_token not in caplog.text
    finally:
        app.dependency_overrides.pop(deps.get_keycloak_verifier, None)


def test_get_auth_me_returns_503_when_keycloak_unavailable():
    verifier = KeycloakVerifier(issuer=ISSUER, jwks_url=JWKS_URL, audience=AUDIENCE)

    def _raise_conn_error(_token: str):
        raise jwt.PyJWKClientConnectionError("Connection refused")

    verifier._jwks.get_signing_key_from_jwt = _raise_conn_error

    with pytest.raises(AuthUnavailableError):
        verifier.verify("any.token.here")

    app.dependency_overrides[deps.get_keycloak_verifier] = lambda: verifier
    try:
        res = client.get(
            "/api/auth/me", headers={"Authorization": "Bearer any.token.here"}
        )
        assert res.status_code == 503
        assert res.json()["detail"] == "Keycloak қолжетімсіз"
    finally:
        app.dependency_overrides.pop(deps.get_keycloak_verifier, None)


def test_keycloak_config_env_overrides_and_swagger_oauth_pkce():
    custom = Settings(
        KEYCLOAK_ISSUER="http://localhost:8080/realms/edu-realm/",
        KEYCLOAK_JWKS_URL="http://keycloak:8080/realms/edu-realm/protocol/openid-connect/certs",
    )
    assert custom.keycloak_issuer == "http://localhost:8080/realms/edu-realm"
    assert (
        custom.keycloak_jwks_url
        == "http://keycloak:8080/realms/edu-realm/protocol/openid-connect/certs"
    )

    derived = Settings(
        KEYCLOAK_SERVER_URL="http://localhost:8080",
        KEYCLOAK_REALM="edu-realm",
        KEYCLOAK_ISSUER=None,
        KEYCLOAK_JWKS_URL=None,
    )
    assert derived.keycloak_issuer == "http://localhost:8080/realms/edu-realm"
    assert (
        derived.keycloak_jwks_url
        == "http://localhost:8080/realms/edu-realm/protocol/openid-connect/certs"
    )

    openapi = client.get("/api/openapi.json").json()
    schemes = openapi["components"]["securitySchemes"]
    oauth = schemes["OAuth2AuthorizationCodeBearer"]["flows"]["authorizationCode"]
    assert oauth["authorizationUrl"].endswith("/protocol/openid-connect/auth")
    assert oauth["tokenUrl"].endswith("/protocol/openid-connect/token")

    docs_html = client.get("/api/docs").text
    assert '"usePkceWithAuthorizationCodeGrant": true' in docs_html
    assert f'"clientId": "{settings.KEYCLOAK_CLIENT_ID}"' in docs_html
