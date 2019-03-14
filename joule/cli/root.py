import click
import os
import shutil
import subprocess
import asyncio

from joule.api.session import Session
from joule.api.node import (node_info)
from joule import errors

from .config import pass_config


@click.command(name="info")
@pass_config
def info(config):
    session = Session(config.url)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(_run(session))
    except errors.ApiError as e:
        raise click.ClickException(str(e)) from e
    finally:
        loop.run_until_complete(
            session.close())
        loop.close()


async def _run(session):
    info = await node_info(session)
    # display info
    click.echo("Server Version: %s" % info.version)
    click.echo("Status: online")


@click.command(name="initialize")
@click.option("--dsn", help="PostgreSQL DSN", required=True)
def initialize(dsn):  # pragma: no cover
    import pkg_resources
    import requests
    click.echo("1. creating joule user ", nl=False)
    proc = subprocess.run("useradd -r -G dialout joule".split(" "), stderr=subprocess.PIPE)
    if proc.returncode == 0:
        click.echo("[" + click.style("OK", fg="green") + "]")
    elif proc.returncode == 1:
        _run_as_root()
    elif proc.returncode == 9:
        click.secho("[" + click.style("EXISTS", fg='yellow') + "]")
    else:
        click.echo("[" + click.style("ERROR", fg='red') + "]\n unknown error [%d] see [man useradd]" % r)
        exit(1)
    click.echo("2. registering system service ", nl=False)
    service_file = pkg_resources.resource_filename(
        "joule", "resources/joule.service")
    try:
        shutil.copy(service_file, "/etc/systemd/system")
        subprocess.run("systemctl enable joule.service".split(" "), stderr=subprocess.PIPE)
        subprocess.run("systemctl start joule.service".split(" "), stderr=subprocess.PIPE)
    except PermissionError:
        _run_as_root()

    click.echo("[" + click.style("OK", fg="green") + "]")

    click.echo("3. copying configuration to /etc/joule ", nl=False)
    _make_joule_directory("/etc/joule")
    # check if main.conf exists
    if not os.path.isfile("/etc/joule/main.conf"):
        conf_template = pkg_resources.resource_filename(
            "joule", "resources/templates/main.conf")
        with open(conf_template, 'r') as template:
            with open("/etc/joule/main.conf", 'w') as conf:
                line = template.readline()
                while line:
                    if "REPLACE_WITH_DSN" in line:
                        conf.write("Database = %s\n" % dsn)
                    else:
                        conf.write(line)
                    line = template.readline()

    # set ownership to joule user
    shutil.chown("/etc/joule/main.conf", user="joule", group="joule")

    # check if module_docs.json exists
    MODULE_DOCS = "/etc/joule/module_docs.json"
    if not os.path.isfile(MODULE_DOCS):
        # try to get the latest copy from wattsworth.net
        r = requests.get('http://docs.wattsworth.net/store/data.json')
        with open(MODULE_DOCS, 'w') as f:
            if r.status_code == 200:
                f.write(r.text)
            else:
                f.write("[]")
    # set ownership to joule user
    shutil.chown(MODULE_DOCS, user="joule", group="joule")
    # give everyone rw access
    os.chmod(MODULE_DOCS, 0o666)

    # setup stream config directory
    _make_joule_directory("/etc/joule/stream_configs")
    example_file = pkg_resources.resource_filename(
        "joule", "resources/templates/stream.example")
    shutil.copy(example_file, "/etc/joule/stream_configs")
    # set ownership to joule user
    shutil.chown("/etc/joule/stream_configs/stream.example",
                 user="joule", group="joule")

    # setup module config directory
    _make_joule_directory("/etc/joule/module_configs")
    example_file = pkg_resources.resource_filename(
        "joule", "resources/templates/module.example")
    shutil.copy(example_file, "/etc/joule/module_configs")
    # set ownership to joule user
    shutil.chown("/etc/joule/module_configs/module.example",
                 user="joule", group="joule")


def _make_joule_directory(path):  # pragma: no cover
    try:
        if os.path.isfile(path):
            click.echo("\n "+click.style("ERROR", fg='red') +
                       " cannot create directory [%s], a file exists with the same name" % path)
            exit(1)
        # check if directory exists
        if not os.path.isdir(path):
            os.makedirs(path)
        # set ownership to joule user
        shutil.chown(path, user="joule", group="joule")
    except PermissionError:
        _run_as_root()


def _run_as_root():  # pragma: no cover
    click.echo("[" + click.style("ERROR", fg="red") + "]\n run as [sudo joule initialize]")
    exit(1)
