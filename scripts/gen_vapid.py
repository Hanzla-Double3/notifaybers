"""Generate a VAPID keypair for Web Push.

Run once:  python scripts/gen_vapid.py
Writes the private key to data/vapid_private.pem and prints the public
key to paste into .env as VAPID_PUBLIC_KEY.
"""

import base64
import os

from py_vapid import Vapid

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUT_PATH = os.path.join(OUT_DIR, "vapid_private.pem")


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    vapid = Vapid()
    vapid.generate_keys()
    vapid.save_key(OUT_PATH)

    numbers = vapid.public_key.public_numbers()
    x = numbers.x.to_bytes(32, "big")
    y = numbers.y.to_bytes(32, "big")
    raw = b"\x04" + x + y
    public_b64 = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    print(f"Private key saved to: {OUT_PATH}")
    print()
    print("Add this to your .env:")
    print(f"VAPID_PUBLIC_KEY={public_b64}")


if __name__ == "__main__":
    main()
