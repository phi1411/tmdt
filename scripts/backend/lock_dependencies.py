"""Freeze installed runtime/dev dependency closures, excluding unrelated tools."""
from importlib.metadata import version, requires
from pathlib import Path
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ['Flask', 'flask-cors', 'PyJWT', 'python-dotenv', 'pymongo', 'argon2-cffi', 'jsonschema']


def closure(names):
    pending = list(names)
    result = {}
    while pending:
        name = canonicalize_name(pending.pop())
        if name in result:
            continue
        result[name] = version(name)
        for spec in requires(name) or []:
            requirement = Requirement(spec)
            if requirement.marker is None or requirement.marker.evaluate({'extra': ''}):
                pending.append(requirement.name)
    return result


if __name__ == '__main__':
    for filename, names in [('requirements.lock.txt', RUNTIME), ('requirements-dev.lock.txt', RUNTIME + ['pytest'])]:
        resolved = closure(names)
        text = '# Resolved and tested on Python 3.12 / Windows. Regenerate after dependency changes.\n'
        for name, value in sorted(resolved.items()):
            # Windows-only packages retain a marker so Linux installs are valid.
            marker = '; sys_platform == "win32"' if name == 'colorama' else ''
            text += f'{name}=={value}{marker}\n'
        (ROOT / 'backend' / filename).write_text(text, encoding='utf-8')
        print(f'{filename}: {len(resolved)} resolved packages')
