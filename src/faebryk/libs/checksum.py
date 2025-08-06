import re
from hashlib import sha256


class Checksum:
    class Mismatch(Exception):
        def __init__(self, stated_checksum: str, actual_checksum: str):
            self.stated_checksum = stated_checksum
            self.actual_checksum = actual_checksum

        def __str__(self):
            return f"Checksum mismatch {self.actual_checksum} != {self.stated_checksum}"

    @staticmethod
    def build(to_hash: str, normalize: bool = True) -> str:
        # normalize line endings and whitespace
        if normalize:
            to_hash = to_hash.replace("\r", "")
            c = r" \t"
            s = rf"[{c}]"
            # replace multiple spaces with one space
            to_hash = re.sub(rf"([^{c}\n]){s}+", r"\1 ", to_hash)
            # space before newline
            to_hash = re.sub(rf"{s}+\n", r"\n", to_hash)
            # remove empty lines
            to_hash = re.sub(r"\n+", r"\n", to_hash)

        return sha256(to_hash.encode("utf-8")).hexdigest()

    @staticmethod
    def verify(stated_checksum: str, to_verify: str):
        actual_checksum = Checksum.build(to_verify)

        if (
            actual_checksum != stated_checksum
            # legacy
            and Checksum.build(to_verify, normalize=False) != stated_checksum
        ):
            raise Checksum.Mismatch(stated_checksum, actual_checksum)
