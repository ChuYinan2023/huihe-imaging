import pytest
from pathlib import Path
from app.services.storage_service import LocalStorage


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(root_dir=tmp_path)


def test_save_and_get(storage):
    data = b"hello world"
    path = storage.save("test/file.txt", data)
    retrieved = storage.get(path)
    assert retrieved == data


def test_delete(storage):
    storage.save("test/file.txt", b"data")
    assert storage.delete("test/file.txt")
    assert not storage.delete("nonexistent.txt")


def test_save_creates_subdirectories(storage, tmp_path):
    storage.save("deep/nested/dir/file.bin", b"data")
    assert (tmp_path / "deep/nested/dir/file.bin").exists()


def test_atomic_move(storage, tmp_path):
    storage.save("tmp/upload.bin", b"data")
    storage.atomic_move("tmp/upload.bin", "final/upload.bin")
    assert not (tmp_path / "tmp/upload.bin").exists()
    assert (tmp_path / "final/upload.bin").exists()
    assert storage.get("final/upload.bin") == b"data"


def test_exists(storage):
    assert not storage.exists("nope.txt")
    storage.save("yes.txt", b"data")
    assert storage.exists("yes.txt")


def test_path_traversal_rejected(storage):
    with pytest.raises(ValueError, match="Path traversal"):
        storage.save("../../etc/passwd", b"hack")
