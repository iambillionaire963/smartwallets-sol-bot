import os
import json
from solders.keypair import Keypair

KEY_DIR = "keys"
os.makedirs(KEY_DIR, exist_ok=True)

def save_keypair(user_id: str, kp: Keypair):
    key_path = f"{KEY_DIR}/{user_id}.json"
    with open(key_path, "w") as f:
        json.dump(list(kp.to_bytes()), f)

def load_keypair(user_id: str) -> Keypair:
    key_path = f"{KEY_DIR}/{user_id}.json"
    with open(key_path, "r") as f:
        key_bytes = bytes(json.load(f))
    return Keypair.from_bytes(key_bytes)

def test_keypair_roundtrip(user_id: str):
    key_path = f"{KEY_DIR}/{user_id}.json"
    
    if os.path.exists(key_path):
        print("🔁 Key already exists, loading...")
        kp = load_keypair(user_id)
    else:
        print("🆕 Creating new key...")
        kp = Keypair()
        save_keypair(user_id, kp)

    pubkey_1 = str(kp.pubkey())
    
    # Load again to verify
    kp_loaded = load_keypair(user_id)
    pubkey_2 = str(kp_loaded.pubkey())

    assert pubkey_1 == pubkey_2, "❌ MISMATCH! Saved and loaded pubkeys are different!"
    print(f"✅ Success! Pubkey = {pubkey_1}")

# Run the test
test_keypair_roundtrip("6805071779")
