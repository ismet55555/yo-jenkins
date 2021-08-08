#!/usr/bin/env python3

import json
import logging
import sys

import click
import xmltodict
from yo_jenkins.cli import cli_utility as cu
from yo_jenkins.cli.cli_utility import log_to_history

# Getting the logger reference
logger = logging.getLogger()


@log_to_history
def info(opt_pretty: bool, opt_yaml: bool, opt_xml: bool, opt_toml: bool, profile: str, node_name: str,
         depth: int) -> None:
    """TODO Docstring

    Details: TODO

    Args:
        TODO

    Returns:
        TODO
    """
    yj = cu.config_yo_jenkins(profile)
    data = yj.Node.info(node_name, depth)
    if not data:
        click.echo(click.style('no node information', fg='bright_red', bold=True))
        sys.exit(1)
    cu.standard_out(data, opt_pretty, opt_yaml, opt_xml, opt_toml)


@log_to_history
def list(opt_pretty: bool, opt_yaml: bool, opt_xml: bool, opt_toml: bool, opt_list: bool, profile: str,
         depth: int) -> None:
    """TODO Docstring

    Details: TODO

    Args:
        TODO

    Returns:
        TODO
    """
    yj = cu.config_yo_jenkins(profile)
    data, data_list = yj.Node.list(depth)
    if not data:
        click.echo(click.style('failed', fg='bright_red', bold=True))
        sys.exit(1)
    data = data_list if opt_list else data
    cu.standard_out(data, opt_pretty, opt_yaml, opt_xml, opt_toml)


@log_to_history
def create_permanent(profile: str, **kwargs) -> None:
    """TODO Docstring

    Details: TODO

    Args:
        TODO

    Returns:
        TODO
    """
    yj = cu.config_yo_jenkins(profile)
    if not yj.Node.create_permanent(**kwargs):
        click.echo(click.style('failed', fg='bright_red', bold=True))
        sys.exit(1)
    click.echo(click.style('success', fg='bright_green', bold=True))


@log_to_history
def delete(profile: str, node_name: str) -> None:
    """TODO Docstring

    Details: TODO

    Args:
        TODO

    Returns:
        TODO
    """
    yj = cu.config_yo_jenkins(profile)
    if not yj.Node.delete(node_name):
        click.echo(click.style('failed', fg='bright_red', bold=True))
        sys.exit(1)
    click.echo(click.style('success', fg='bright_green', bold=True))


@log_to_history
def disable(profile: str, node_name: str, message: str) -> None:
    """TODO Docstring

    Details: TODO

    Args:
        TODO

    Returns:
        TODO
    """
    yj = cu.config_yo_jenkins(profile)
    if not yj.Node.disable(node_name, message):
        click.echo(click.style('failed', fg='bright_red', bold=True))
        sys.exit(1)
    click.echo(click.style('success', fg='bright_green', bold=True))


@log_to_history
def enable(profile: str, node_name: str, message: str) -> None:
    """TODO Docstring

    Details: TODO

    Args:
        TODO

    Returns:
        TODO
    """
    yj = cu.config_yo_jenkins(profile)
    if not yj.Node.enable(node_name, message):
        click.echo(click.style('failed', fg='bright_red', bold=True))
        sys.exit(1)
    click.echo(click.style('success', fg='bright_green', bold=True))

@log_to_history
def config(opt_pretty: bool, opt_yaml: bool, opt_xml: bool, opt_toml: bool, opt_json: bool, profile: str, node_name: str,
           filepath: str) -> None:
    """TODO Docstring

    Details: TODO

    Args:
        TODO

    Returns:
        TODO
    """
    yj = cu.config_yo_jenkins(profile)
    data, write_success = yj.Node.config(filepath=filepath,
                                                node_name=node_name,
                                                opt_json=opt_json,
                                                opt_yaml=opt_yaml,
                                                opt_toml=opt_toml)
    if not data:
        click.echo(click.style('failed', fg='bright_red', bold=True))
        sys.exit(1)

    if not write_success:
        click.echo(click.style('failed to write', fg='bright_red', bold=True))
        sys.exit(1)

    opt_xml = not any([opt_json, opt_yaml, opt_toml])
    data = data if opt_xml else json.loads(json.dumps(xmltodict.parse(data)))
    cu.standard_out(data, opt_pretty, opt_yaml, opt_xml, opt_toml)

@log_to_history
def reconfig(profile: str, node_name: str, filepath: str, as_json: str) -> None:
    """TODO Docstring

    Details: TODO

    Args:
        TODO

    Returns:
        TODO
    """
    yj = cu.config_yo_jenkins(profile)
    success = yj.Node.reconfig(filepath=filepath, node_name=node_name, as_json=as_json)
    if not success:
        click.echo(click.style('failed', fg='bright_red', bold=True))
        sys.exit(1)
    click.echo(click.style('success', fg='bright_green', bold=True))
