#!/usr/bin/env python3
"""Copy this complete installed Agent Skill, without cache/run directories.

This does not grant execution privileges; a supported Codex environment is needed.
"""
import argparse
import os
from pathlib import Path
import shutil

SKILL_NAME='nopc-cae-cloud-bridge'
SKIP={'runs','.venv','.pytest_cache','__pycache__','.git','dist','build','.ruff_cache'}


def install(project, target, force=False):
    project=Path(project).resolve()
    target=Path(target).expanduser().resolve()
    dest=target/SKILL_NAME
    if not (project/'SKILL.md').is_file() or not (project/'src'/'nopc_bridge').is_dir():
        raise ValueError('not a valid NoPC CAE Cloud Bridge source directory')
    if dest.exists():
        if not force:raise FileExistsError('skill exists; pass --force to replace')
        if dest.is_symlink():raise ValueError('refusing to overwrite symlink installation')
        shutil.rmtree(dest)
    target.mkdir(parents=True,exist_ok=True)
    shutil.copytree(project,dest,ignore=shutil.ignore_patterns(*SKIP,'*.pyc','*.egg-info'))
    assert (dest/'SKILL.md').is_file()
    return dest


def main():
    p=argparse.ArgumentParser(description='Install Skill sources to agent skills directory')
    p.add_argument('--target',default='~/.agents/skills',help='Parent directory, not full skill directory')
    p.add_argument('--force',action='store_true')
    a=p.parse_args()
    print('Installed:',install(Path(__file__).resolve().parent.parent,a.target,a.force))

if __name__=='__main__':main()
