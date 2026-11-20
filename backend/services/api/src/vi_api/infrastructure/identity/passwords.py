from hashlib import scrypt
from secrets import compare_digest, token_bytes

from anyio import CapacityLimiter, to_thread

LIMIT = CapacityLimiter(2)
DUMMY_HASH = f"{'00' * 16}:{'00' * 32}"


def derive(password: str, salt: bytes) -> bytes:
    return scrypt(password.encode(), salt=salt, n=2**15, r=8, p=3, dklen=32, maxmem=64 * 1024**2)


def hash_password(password: str) -> str:
    salt = token_bytes(16)
    return f"{salt.hex()}:{derive(password, salt).hex()}"


class ScryptPasswordVerifier:
    async def verify(self, password: str, stored_hash: str | None) -> bool:
        salt, digest = (stored_hash or DUMMY_HASH).split(":")
        actual = await to_thread.run_sync(derive, password, bytes.fromhex(salt), limiter=LIMIT)
        return compare_digest(actual, bytes.fromhex(digest)) and stored_hash is not None
