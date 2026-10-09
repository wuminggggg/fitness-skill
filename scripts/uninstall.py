"""Uninstall only fitness-skill. Default: preview; --yes explicitly deletes it."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import stat

SKILL_NAME = 'fitness-skill'

def default_skills_dir() -> Path:
    return Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex') / 'skills'

def is_link(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & 0x400)

def inspect_target(skills_dir: Path) -> tuple[Path, list[Path]]:
    parent = skills_dir.expanduser().resolve()
    candidate = parent / SKILL_NAME
    if not candidate.exists() and not candidate.is_symlink():
        return candidate, []
    if is_link(candidate):
        raise ValueError('Refusing symlink or junction skill directory')
    target = candidate.resolve(strict=True)
    if target.parent != parent or target.name != SKILL_NAME or not target.is_dir():
        raise ValueError('Uninstall target is outside the exact skill directory')
    paths = []
    # Do not descend into reparse points, including Windows junctions.
    for directory, folders, files in os.walk(target, followlinks=False):
        for name in folders + files:
            path = Path(directory) / name
            if is_link(path):
                raise ValueError('Refusing skill containing symlinks or junctions')
            if path.resolve().is_relative_to(target) is False:
                raise ValueError('Unexpected path outside skill')
            if name == 'snapshot.json' or (name == 'data' and path.is_dir()):
                raise ValueError('Training data found inside skill; move it to a separate data directory before uninstalling')
            paths.append(path)
    marker = target / 'SKILL.md'
    if not marker.is_file():
        raise ValueError('SKILL.md missing; refusing to delete an unidentified directory')
    text = marker.read_text(encoding='utf-8-sig')
    frontmatter = re.match(r'\A---\s*\n(.*?)\n---(?:\s|$)', text, re.S)
    if not frontmatter or not re.search(r'^name:\s*fitness-skill\s*$', frontmatter[1], re.M):
        raise ValueError('SKILL.md name does not match fitness-skill')
    return target, paths

def uninstall(skills_dir: Path, execute: bool = False) -> dict:
    target, paths = inspect_target(skills_dir)
    if not target.exists():
        return {'status':'not_installed', 'target':str(target)}
    result = {'status':'preview', 'target':str(target), 'files':sum(p.is_file() for p in paths),
              'data_policy':'Only the skill directory is removed. External training data, project copies and archives are preserved.'}
    if execute:
        # Recheck immediately before recursive deletion, against the same exact root.
        checked, _ = inspect_target(skills_dir)
        if checked != target:
            raise ValueError('Uninstall target changed')
        if Path.cwd().resolve().is_relative_to(target):
            os.chdir(target.parent)
        shutil.rmtree(target)
        if target.exists():
            raise OSError('Uninstall incomplete')
        result['status'] = 'uninstalled'
    return result

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skills-dir', type=Path, default=default_skills_dir(), help='Parent skills directory; child name is fixed to fitness-skill')
    parser.add_argument('--yes', action='store_true', help='Delete the validated skill directory; omission only previews')
    args = parser.parse_args()
    try:
        print(json.dumps(uninstall(args.skills_dir,args.yes),ensure_ascii=False,indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(2,f'Uninstall refused or incomplete: {exc}\n')

if __name__ == '__main__':
    main()
