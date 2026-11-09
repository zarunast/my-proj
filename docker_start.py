"""Prepare a mounted data directory, then run the app without root privileges."""
import os
from pathlib import Path


def main():
    if os.geteuid() == 0:
        storage = Path(os.environ.get('DATA_DIR', '/data')).resolve()
        if storage in (Path('/'), Path('/app')):
            raise RuntimeError('DATA_DIR must be a dedicated data directory')
        storage.mkdir(parents=True, exist_ok=True)
        paths = [storage, *(storage / name for name in ('couples.sqlite3', 'couples.sqlite3-wal', 'couples.sqlite3-shm', 'couples.sqlite3-journal'))]
        for path in paths:
            if path.is_symlink():
                raise RuntimeError('Database paths must not be symbolic links')
            if path.exists():
                os.chown(path, 10001, 10001)
        os.setgroups([])
        os.setgid(10001)
        os.setuid(10001)
    os.execvp('python', ['python', 'server.py'])


if __name__ == '__main__':
    main()
