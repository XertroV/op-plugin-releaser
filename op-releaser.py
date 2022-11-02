#!/usr/bin/env python3

import logging
import os
from pathlib import Path
import subprocess
from typing import Literal

import click
import toml
from git import Repo

logging.basicConfig(level=logging.INFO)

VersionTuple = tuple[int, int, int]
BumpLevel = Literal["major"] | Literal["minor"] | Literal["patch"]


def read_info_toml_version() -> VersionTuple:
    info_toml = Path('info.toml')
    if not info_toml.exists():
        raise Exception('no ./info.toml file')
    info = toml.load(info_toml)
    version: str = info['meta']['version']
    plugin_name: str = info['meta']['name']
    logging.info(f"[{plugin_name}] Read info.toml for version: {version}")
    return version_from_str(version)


def update_info_toml_version(prior_ver: VersionTuple, new_ver: VersionTuple):
    info_toml = Path('info.toml')
    if not info_toml.exists():
        raise Exception('no ./info.toml file')
    info_str = info_toml.read_text()
    pv_str = version_to_str(prior_ver)
    if pv_str not in info_str:
        raise Exception(f'Could not find `{pv_str}` in info.toml')
    if info_str.find(pv_str) != info_str.rfind(pv_str):
        raise Exception(f'More than one occurance of {pv_str} -- bailing')
    info_str = info_str.replace(pv_str, version_to_str(new_ver))
    info_toml.write_text(info_str)
    logging.info(f"Wrote new {info_toml} with updated version: {version_to_str(new_ver)}")


def version_to_str(ver: VersionTuple) -> str:
    return ".".join(map(str, ver))


def version_from_str(version: str) -> VersionTuple:
    parts = version.split(".")
    if len(parts) != 3:
        raise Exception('expected version to be of the form X.Y.Z')
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def bump_version(ver: VersionTuple, bump_level: BumpLevel):
    if bump_level == "major":
        return (ver[0] + 1, 0, 0)
    if bump_level == "minor":
        return (ver[0], ver[1] + 1, 0)
    if bump_level == "patch":
        return (ver[0], ver[1], ver[2] + 1)
    raise Exception(f"bump_level provided was {bump_level}, which is an invalid choice.")


def git_get_repo() -> Repo:
    return Repo(os.curdir)


def git_check_in_repo():
    repo = git_get_repo()
    if repo is None or repo.bare:
        return False
    return True


def git_commit_version(prior_ver: VersionTuple, ver: VersionTuple):
    repo = git_get_repo()
    repo.git.add('info.toml')
    repo.git.commit(m=f"Version: {version_to_str(ver)}")
    repo.git.tag(version_to_str(ver))
    logging.info(f"Committed version bump from {version_to_str(prior_ver)} to {version_to_str(ver)}")


def build_plugin(ver: VersionTuple):
    proc = subprocess.Popen(['./build.sh release'], shell=True, stdout=subprocess.PIPE)
    logging.info(proc.stdout.read().decode("UTF8"))
    logging.info(f"Built plugin: {version_to_str(ver)}; return code: {proc.returncode}")


def git_commit_new_release(ver: VersionTuple):
    repo = git_get_repo()
    repo.git.add("./*.op")
    repo.git.commit(m=f"Release: {version_to_str(ver)}")
    logging.info(f"Committed build for version: {version_to_str(ver)}")


def run_release(bump_level: BumpLevel):
    if not git_check_in_repo():
        raise Exception('not in a git repo!')
    prior_ver = read_info_toml_version()
    ver = bump_version(prior_ver, bump_level)
    update_info_toml_version(prior_ver, ver)
    git_commit_version(prior_ver, ver)
    build_plugin(ver)
    git_commit_new_release(ver)


@click.group()
def cli():
    pass

@cli.group()
def release():
    pass

@release.command()
def patch():
    run_release(bump_level="patch")

@release.command()
def minor():
    run_release(bump_level="minor")

@release.command()
def major():
    run_release(bump_level="major")


if __name__ == '__main__':
    cli()
