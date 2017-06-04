#!/usr/bin/env python
#
# just-install - The stupid package installer
#
# Copyright (C) 2013-2016  Lorenzo Villani
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import absolute_import, division, print_function, unicode_literals

import contextlib
import glob
import json
import os
import zipfile
from subprocess import check_call

import requests

HERE = os.path.dirname(__file__)
TOP_LEVEL = os.path.abspath(os.path.join(HERE, ".."))

with open(os.path.join(TOP_LEVEL, ".releng.json"), "r") as f:
    VERSION = json.load(f)["version"]


def main():
    os.chdir(TOP_LEVEL)

    if is_stable_build():
        os.environ["JUST_INSTALL_MSI_VERSION"] = VERSION
    else:
        os.environ["JUST_INSTALL_MSI_VERSION"] = "255"

    clean()
    build()
    build_msi()
    deploy()


def clean():
    def remove(*args):
        for arg in args:
            try:
                os.remove(arg)
            except:
                pass

    remove("just-install")
    remove(*glob.glob("*.exe"))
    remove(*glob.glob("*.msi"))
    remove(*glob.glob("*.wixobj"))
    remove(*glob.glob("*.wixpdb"))


def build():
    with scoped_environ("GOARCH", "386"):
        call(
            "go", "build", "-o", "just-install.exe",
            "-ldflags", "-X main.version={}".format(VERSION), "./bin")


@contextlib.contextmanager
def scoped_environ(name, value):
    try:
        os.environ[name] = value
        yield
    finally:
        del os.environ[name]


def build_msi():
    call("candle", "just-install.wxs")
    call("light", "just-install.wixobj")


def deploy():
    if is_stable_build():
        target = "stable"
    else:
        target = "unstable"

    print("Deploying to {}".format(target))

    # Create zip archive for API-driven deployment
    with zipfile.ZipFile("deploy.zip", "w") as zipfileobj:
        zipfileobj.write("just-install.exe")
        zipfileobj.write("just-install.msi")

    # Push zip archive to Netlify
    deploy_url = "https://api.netlify.com/api/v1/sites/just-install-{}.netlify.com/deploys".format(
        target)

    with open("deploy.zip", "r") as fileobj:
        requests.post(
            deploy_url,
            data=fileobj,
            headers={
                "Authorization": "Bearer {}".format(os.environ["NETLIFY_DEPLOY_TOKEN"]),
                "Content-Type": "application/zip",
            },
            timeout=60)


def call(*args):
    print("+", " ".join(args))
    check_call(args)


def is_stable_build():
    return "APPVEYOR_REPO_TAG_NAME" in os.environ


if __name__ == "__main__":
    main()
