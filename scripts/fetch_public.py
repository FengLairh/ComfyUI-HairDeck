"""Resumable parallel downloads for public release files; never log redirect URLs."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from pathlib import Path
import re
import time

import requests


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _fetch(url, destination, sha256=None, workers=8):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and sha256 and digest(destination) == sha256:
        print('PRESENT', destination.name, flush=True)
        return destination
    headers = {'Accept-Encoding': 'identity', 'Range': 'bytes=0-0'}
    with requests.get(url, headers=headers, stream=True, timeout=(15, 45)) as r:
        r.raise_for_status()
        match = re.fullmatch(r'bytes 0-0/(\d+)', r.headers.get('Content-Range', ''))
        total = int(match[1]) if r.status_code == 206 and match else None
    parts = destination.with_name(destination.name + '.parts')
    parts.mkdir(exist_ok=True)
    if total is None:
        # Small files / hosts without range support: a single verified transfer.
        temporary = destination.with_name(destination.name + '.partial')
        with requests.get(url, stream=True, timeout=(15, 90)) as r:
            r.raise_for_status()
            with open(temporary, 'wb') as f:
                for block in r.iter_content(1024 * 1024):
                    f.write(block)
        if sha256 and digest(temporary) != sha256:
            raise RuntimeError('SHA256 mismatch: ' + destination.name)
        temporary.replace(destination)
        print('VERIFIED', destination.name, destination.stat().st_size, flush=True)
        return destination
    chunk = 8 * 1024 * 1024
    ranges = [(i, start, min(start + chunk, total) - 1)
              for i, start in enumerate(range(0, total, chunk))]

    def download(item):
        i, first, last = item
        part = parts / f'{i:05}.part'
        expected = last - first + 1
        if part.is_file() and part.stat().st_size == expected:
            return i
        for attempt in range(4):
            offset = part.stat().st_size if part.is_file() else 0
            if offset > expected:
                raise RuntimeError('Unexpected chunk size: ' + destination.name)
            try:
                h = {'Accept-Encoding': 'identity', 'Range': f'bytes={first + offset}-{last}'}
                with requests.get(url, headers=h, stream=True, timeout=(15, 60)) as r:
                    r.raise_for_status()
                    wanted = f'bytes {first + offset}-{last}/{total}'
                    if r.status_code != 206 or r.headers.get('Content-Range') != wanted:
                        raise RuntimeError('Server did not honor requested byte range')
                    with open(part, 'ab') as f:
                        for block in r.iter_content(256 * 1024):
                            f.write(block)
                if part.stat().st_size != expected:
                    raise RuntimeError('Incomplete chunk')
                return i
            except Exception as error:
                if attempt == 3:
                    # Error messages may contain signed download URLs.
                    raise RuntimeError(f'{destination.name}: chunk {i} failed ({type(error).__name__})') from None
                time.sleep(2 + attempt)

    print('DOWNLOAD', destination.name, total, 'bytes', flush=True)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        done = 0
        for future in as_completed([pool.submit(download, item) for item in ranges]):
            future.result()
            done += 1
            if done == len(ranges) or done % 8 == 0:
                print('PROGRESS', destination.name, f'{done}/{len(ranges)} chunks', flush=True)
    temporary = destination.with_name(destination.name + '.partial')
    with open(temporary, 'wb') as output:
        for i, _, _ in ranges:
            with open(parts / f'{i:05}.part', 'rb') as source:
                for block in iter(lambda: source.read(4 * 1024 * 1024), b''):
                    output.write(block)
    if temporary.stat().st_size != total or (sha256 and digest(temporary) != sha256):
        raise RuntimeError('Size or SHA256 mismatch: ' + destination.name)
    temporary.replace(destination)
    # Only remove our completed chunk files, after integrity verification.
    for i, _, _ in ranges:
        (parts / f'{i:05}.part').unlink()
    parts.rmdir()
    print('VERIFIED', destination.name, total, flush=True)
    return destination


def fetch(url, destination, sha256=None, workers=8):
    for attempt in range(4):
        try:
            return _fetch(url, destination, sha256, workers)
        except requests.RequestException as error:
            if attempt == 3:
                raise RuntimeError(f'{Path(destination).name}: connection failed ({type(error).__name__})') from None
            print('RETRY_CONNECTION', Path(destination).name, attempt + 1, type(error).__name__, flush=True)
            time.sleep(2 + attempt)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', required=True)
    ap.add_argument('--destination', required=True)
    ap.add_argument('--sha256')
    args = ap.parse_args()
    fetch(args.url, args.destination, args.sha256)
