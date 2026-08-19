"""Backend selection and role-filter dialects."""

import pytest

from app import vectorstores


def test_default_backend_is_chroma():
    assert vectorstores.get_backend("chroma").name == "chroma"


def test_unknown_backend_is_rejected():
    with pytest.raises(ValueError, match="Unknown VECTOR_STORE"):
        vectorstores.get_backend("redis")


@pytest.mark.parametrize("backend_name", ["chroma", "pinecone"])
def test_admin_is_unfiltered(backend_name):
    assert vectorstores.get_backend(backend_name).role_filter("Admin") is None


@pytest.mark.parametrize("backend_name", ["chroma", "pinecone"])
def test_department_role_sees_own_plus_general(backend_name):
    f = vectorstores.get_backend(backend_name).role_filter("Finance")
    assert f == {"role": {"$in": ["finance", "general"]}}


@pytest.mark.parametrize("backend_name", ["chroma", "pinecone"])
def test_role_is_case_insensitive(backend_name):
    backend = vectorstores.get_backend(backend_name)
    assert backend.role_filter("HR") == backend.role_filter("hr")


@pytest.mark.parametrize("backend_name", ["chroma", "pinecone"])
def test_no_role_ever_leaks_another_department(backend_name):
    f = vectorstores.get_backend(backend_name).role_filter("HR")
    allowed = f["role"].get("$in") or [f["role"].get("$eq")]
    assert "finance" not in allowed and "compliance" not in allowed


def test_backends_disagree_on_single_value_dialect():
    """The reason this abstraction exists.

    Chroma accepts a bare equality map; Pinecone wants an explicit operator.
    Hardcoding either dialect would silently break the other backend.
    """
    assert vectorstores.get_backend("chroma").role_filter("general") == {"role": "general"}
    assert vectorstores.get_backend("pinecone").role_filter("general") == {
        "role": {"$eq": "general"}
    }


def test_pinecone_backend_requires_a_key(monkeypatch):
    from app import config

    monkeypatch.setattr(config, "PINECONE_API_KEY", None)
    with pytest.raises(config.MissingCredentialError, match="PINECONE_API_KEY"):
        vectorstores.get_backend("pinecone").create(embeddings=None)


def test_pinecone_missing_libraries_gives_install_instructions(monkeypatch):
    """A missing optional dependency must name the fix, not just the module."""
    import builtins

    from app import config

    monkeypatch.setattr(config, "PINECONE_API_KEY", "fake-key")
    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name.startswith(("pinecone", "langchain_pinecone")):
            raise ImportError(f"No module named {name!r}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    with pytest.raises(ImportError, match="requirements-pinecone.txt"):
        vectorstores.get_backend("pinecone").create(embeddings=None)
