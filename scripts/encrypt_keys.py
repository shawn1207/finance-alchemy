import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.infrastructure.security.vault import encrypt_secret

def encrypt_env_file(env_path: str = '.env'):
    if not os.path.exists(env_path):
        print(f"❌ Error: {env_path} not found.")
        return

    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    encrypted_lines = []
    sensitive_keys = ['OPENAI_API_KEY', 'EASTMONEY_API_KEY', 'TUSHARE_TOKEN']

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            encrypted_lines.append(line)
            continue
        
        if '=' in line:
            key, val = line.split('=', 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            
            if key in sensitive_keys and val and not val.startswith('gAAAA'):
                print(f"🔒 Encrypting {key}...")
                encrypted_val = encrypt_secret(val)
                encrypted_lines.append(f'{key}="{encrypted_val}"')
            else:
                encrypted_lines.append(line)
        else:
            encrypted_lines.append(line)

    backup_path = env_path + '.bak'
    os.rename(env_path, backup_path)
    print(f"💾 Backup created at {backup_path}")

    with open(env_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(encrypted_lines) + '\n')
    
    print(f"✅ Successful! {env_path} has been updated with encrypted values.")

if __name__ == "__main__":
    encrypt_env_file()
