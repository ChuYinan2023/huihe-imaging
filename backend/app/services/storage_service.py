import os
from abc import ABC, abstractmethod
from pathlib import Path


class StorageService(ABC):
    @abstractmethod
    def save(self, path: str, data: bytes) -> str: ...

    @abstractmethod
    def get(self, path: str) -> bytes: ...

    @abstractmethod
    def delete(self, path: str) -> bool: ...

    @abstractmethod
    def get_url(self, path: str) -> str: ...

    @abstractmethod
    def atomic_move(self, src: str, dst: str) -> None: ...

    @abstractmethod
    def exists(self, path: str) -> bool: ...


class LocalStorage(StorageService):
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _full_path(self, path: str) -> Path:
        resolved = (self.root_dir / path).resolve()
        if not str(resolved).startswith(str(self.root_dir.resolve())):
            raise ValueError("Path traversal detected")
        return resolved

    def save(self, path: str, data: bytes) -> str:
        full = self._full_path(path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)
        return path

    def get(self, path: str) -> bytes:
        return self._full_path(path).read_bytes()

    def delete(self, path: str) -> bool:
        full = self._full_path(path)
        if full.exists():
            full.unlink()
            return True
        return False

    def get_url(self, path: str) -> str:
        return f"/storage/{path}"

    def atomic_move(self, src: str, dst: str) -> None:
        src_path = self._full_path(src)
        dst_path = self._full_path(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(str(src_path), str(dst_path))

    def exists(self, path: str) -> bool:
        return self._full_path(path).exists()
