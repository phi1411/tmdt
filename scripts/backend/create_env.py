"""Create a private JWT secret once; preserve all existing real credentials."""
import secrets
from pathlib import Path

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    path = root / '.env'
    text = path.read_text(encoding='utf-8') if path.exists() else (root / '.env.example').read_text(encoding='utf-8')
    lines = text.splitlines()
    found = False
    changed = False
    for index, line in enumerate(lines):
        if line.startswith('JWT_SECRET='):
            found = True
            value = line.split('=', 1)[1].strip()
            if not value or value.startswith('REPLACE_'):
                lines[index] = 'JWT_SECRET=' + secrets.token_urlsafe(48)
                changed = True
    if not found:
        lines.append('JWT_SECRET=' + secrets.token_urlsafe(48))
        changed = True
    if changed or not path.exists():
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('Development .env prepared; existing real secrets preserved, no values printed.')
