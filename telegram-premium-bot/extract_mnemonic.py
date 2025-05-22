from solders.keypair import Keypair
from bip_utils import Bip39MnemonicGenerator
import json

# Replace this with your actual filename (e.g., 847392.json)
user_id = "123456"
file_path = f"telegram-premium-bot/keys/{7851863021}.json"

# Load the key bytes from the file
with open(file_path) as f:
    key_bytes = bytes(json.load(f))  # 64 bytes: private key + public key

# Extract just the private key (first 32 bytes)
private_key = key_bytes[:32]

# Generate a mnemonic from the private key
mnemonic = Bip39MnemonicGenerator().FromEntropy(private_key)
print("Frase mnemotécnica:", mnemonic)
