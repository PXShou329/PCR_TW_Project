from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCKERIGNORE = ROOT / ".dockerignore"


def test_private_runtime_material_is_excluded_from_docker_build_context() -> None:
    entries = [
        line.strip()
        for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert ".env" in entries
    assert ".env.*" in entries
    assert "**/.env" in entries
    assert "**/.env.*" in entries
    assert "!.env.example" in entries
    assert entries.index(".env.*") < entries.index("!.env.example")
    assert entries.index("**/.env.*") < entries.index("!.env.example")
    assert ".runtime" in entries
    for pattern in (
        "*.dump",
        "*.backup",
        "*.pem",
        "*.key",
        "*.p12",
        "*.pfx",
        "**/id_rsa",
        "**/id_ed25519",
    ):
        assert pattern in entries
