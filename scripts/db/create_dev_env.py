"""Create ignored development config and a private credential note once."""
import secrets
from pathlib import Path

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    config = root / '.env'
    if config.exists():
        print('Existing .env preserved; set SEED_DEMO_PASSWORD if needed.')
    else:
        password = secrets.token_urlsafe(24)
        template = (root / '.env.example').read_text(encoding='utf-8')
        config.write_text(template.replace('SEED_DEMO_PASSWORD=\n', f'SEED_DEMO_PASSWORD={password}\n'), encoding='utf-8')
        note = root / '.local/demo-credentials.md'
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text(f'# Chỉ dùng development local\n\nAdmin: admin@example.test\n\nCustomer: customer01@example.test\n\nPassword fixture: `{password}`\n\nKhông dùng ở production; không commit file này. Chưa có API login ở phase03.\n', encoding='utf-8')
        print('Created ignored .env and .local/demo-credentials.md; password not printed.')
