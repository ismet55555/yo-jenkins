"""Tools Menu CLI Entrypoints"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from pprint import pprint
from typing import NoReturn, Union

import click

from yojenkins.cli import cli_utility as cu
from yojenkins.cli.cli_utility import log_to_history
from yojenkins.tools import SharedLibrary
from yojenkins.utility.utility import (
    browser_open,
    fail_out,
    html_clean,
    item_exists_in_folder,
    load_contents_from_local_file,
    name_to_url,
    print2,
    warn_out,
)

# Getting the logger reference
log = logging.getLogger()

# TODO: Move all these configs to a central config file
BUG_REPORT_URL = "https://github.com/ismet55555/yojenkins/issues/new?assignees=ismet55555&labels=bug%2Ctriage&template=bug_report.yml&title=%5BBug%5D%3A+"
FEATURE_REQUEST_URL = "https://github.com/ismet55555/yojenkins/issues/new?assignees=ismet55555&labels=feature-request&template=feature_request.yml&title=%5BFeature-Request%5D%3A+"
DOCS_URL = "https://www.yojenkins.com/"


@log_to_history
def documentation() -> Union[NoReturn, None]:
    """TODO Docstring

    Details: TODO

    Args:
        TODO
    """
    log.debug(f'Opening documentation in web browser: "{DOCS_URL}" ...')
    success = browser_open(url=DOCS_URL)
    if success:
        log.debug('Successfully opened in web browser')
    else:
        log.debug('Failed to open in web browser')


@log_to_history
def bug_report() -> Union[NoReturn, None]:
    """TODO Docstring

    Details: TODO

    Args:
        TODO
    """
    log.debug(f'Opening bug report webpage in web browser: "{BUG_REPORT_URL}" ...')
    success = browser_open(url=BUG_REPORT_URL)
    if success:
        log.debug('Successfully opened in web browser')
    else:
        log.debug('Failed to open in web browser')


@log_to_history
def feature_request() -> Union[NoReturn, None]:
    """TODO Docstring

    Details: TODO

    Args:
        TODO
    """
    log.debug(f'Opening feature request webpage in web browser: "{FEATURE_REQUEST_URL}" ...')
    success = browser_open(url=FEATURE_REQUEST_URL)
    if success:
        log.debug('Successfully opened in web browser')
    else:
        log.debug('Failed to open in web browser')


def history(profile: str, clear: bool) -> Union[NoReturn, None]:
    """Displaying the command history and clearing the history file if requested.

    ### TODO: Ability to clear only for a specific profile.

    Args:
        profile: The name of the profile to to filter history with
        clear:   Clearing the history file
    """
    # Load contents from history file
    history_file_path = os.path.join(os.path.join(Path.home(), cu.CONFIG_DIR_NAME), cu.HISTORY_FILE_NAME)
    contents = load_contents_from_local_file('json', history_file_path)
    if not contents:
        click.secho('No history found', fg='bright_red', bold=True)
        sys.exit(1)

    # Clearing the history file if requested
    if clear:
        log.debug(f'Removing history file: {history_file_path} ...')
        try:
            os.remove(history_file_path)
        except (OSError, IOError, PermissionError) as error:
            fail_out(f'Failed to clear history file. Exception: {error}')
        log.debug('Successfully cleared history file')
        click.secho('success', fg='bright_green', bold=True)
        sys.exit(0)

    # Displaying the command history
    log.debug(f'Displaying command history for profile "{profile}" ...')

    def output_history_to_console(command_list: list, profile_name: str) -> None:
        """Helper function to format and output to console"""
        for command_info in command_list:
            profile_str = f'{click.style("[" + profile_name + "]", fg="yellow", bold=True)}'
            datetime_str = f'{click.style("[" + command_info["datetime"] + "]", fg="green", bold=False)}'
            tool_version = f'{click.style("[" + "v" + command_info["tool_version"] + "]", fg="green", bold=False)}'

            command_info = f'{profile_str} {datetime_str} {tool_version} - {command_info["tool_path"]} {command_info["arguments"]}'
            click.echo(command_info)

    if profile:
        if profile in contents:
            output_history_to_console(contents[profile], profile)
        else:
            fail_out(f'No history found for profile: {profile}')
    else:
        for profile_name in contents:
            output_history_to_console(contents[profile_name], profile_name)


@log_to_history
def rest_request(profile: str, token: str, request_text: str, request_type: str, raw: bool, clean_html: bool) -> None:
    """Send a generic REST request to Jenkins Server using the loaded credentials

    Args:
        profile: The name of the credentials profile
        token:   API token for Jenkins server
        request_text: The text of the request to send
        request_type: The type of request to send
        raw: Whether to return the raw response or formatted JSON
        clean_html: Whether to clean the HTML tags from the response
    """
    yj_obj = cu.config_yo_jenkins(profile, token)
    request_text = request_text.strip('/')
    content, header, success = yj_obj.rest.request(
        target=request_text,
        request_type=request_type,
        json_content=(not raw),
    )

    if not success:
        fail_out('Failed to make request')

    if request_type == 'HEAD':
        print2(header)
        sys.exit(0)

    if content:
        if clean_html:
            try:
                print2(html_clean(content))
            except Exception:
                print2(content)
        else:
            try:
                print2(json.dumps(content, indent=4))
            except Exception:
                print2(content)
    else:
        fail_out('Content returned, however possible HTML content. Try --raw.')


@log_to_history
def run_script(profile: str, token: str, text: str, file: str, output: str) -> Union[NoReturn, None]:
    """TODO

    Details: TODO:

    Args:
        TODO
    """
    yj_obj = cu.config_yo_jenkins(profile, token)

    # Prepare the commands/script
    script = ''
    if text:
        text = text.strip().replace('  ', ' ')
        script = text
    elif file:
        log.debug(f'Loading specified script from file: {file} ...')
        try:
            with open(os.path.join(file), 'r') as open_file:
                script = open_file.read()
            script_size = os.path.getsize(file)
            log.debug(f'Successfully loaded script file ({script_size} Bytes)')
        except FileNotFoundError as error:
            fail_out(f'Failed to find specified script file ({file})')
        except (OSError, IOError, PermissionError) as error:
            fail_out(f'Failed to read specified script file ({file}). Exception: {error}')

    # Send the request to the server
    content, _, success = yj_obj.rest.request(target='scriptText',
                                              request_type='post',
                                              data={'script': script},
                                              json_content=False)

    if not success:
        fail_out('Failed to make script run request')

    # Save script result to file
    if output:
        log.debug(f'Saving script result into file: {output} ...')
        try:
            with open(output, 'w+') as open_file:
                open_file.write(content)
            log.debug('Successfully wrote script result to file')
        except (OSError, IOError, PermissionError) as error:
            fail_out(f"Failed to write script output to file. Exception: {error}")

    click.echo(content)


@log_to_history
def shared_lib_setup(profile: str, token: str, **kwargs) -> Union[NoReturn, None]:
    """Sets up a shared library on the Jenkins Server

    Args:
        profile: The name of the credentials profile
        token:   API Token for Jenkins server

    Returns:
        True if the setup was successful, else False
    """
    yj_obj = cu.config_yo_jenkins(profile, token)
    data = SharedLibrary().setup(yj_obj.rest, **kwargs)
    if not data:
        fail_out('failed')
    click.secho('success', fg='bright_green', bold=True)


@log_to_history
def test(profile: str, token: str, **kwargs) -> Union[NoReturn, None]:
    """TESTING."""
    yj_obj = cu.config_yo_jenkins(profile, token)

    # Load config file
    #    IDEA: Load a remote configuration file, with URL as argument
    yojenkins_file = os.path.join(os.getcwd(), "yojenkins.yaml")
    run_configs = load_contents_from_local_file('yaml', yojenkins_file)
    pprint(run_configs)
    if not run_configs:
        fail_out(f'Failed to load config file: {yojenkins_file}')

    # TODO: Run through jsonschema

    # ----------------------------------------------------------
    # CREATE TASKS
    # ----------------------------------------------------------
    # item_types = ["folder", "job"]
    # for item_type in item_types:
    #     for item in run_configs["create"][item_type]:
    #         item_name = item["name"]
    #         folder_name = item["folder"]
    #         config_file = item["config_file"]
    #         skip_if_exists = item["skip_if_exists"]
    #
    #         if config_file and not os.path.exists(config_file):
    #             fail_out(f"Failed to find the specified {item_type} config file: {config_file}")
    #         folder_url = name_to_url(yj_obj.rest.get_server_url(), folder_name)
    #
    #         if item_exists_in_folder(item_name, folder_url, item_type, yj_obj.rest):
    #             log.debug(
    #                 f'{item_type.title()} "{item_name}" already exists in '
    #                 f'folder "{folder_url}". Skipping ...'
    #             )
    #         else:
    #             yj_obj.folder.create(
    #                 name=item_name,
    #                 type=item_type,
    #                 folder_name=folder_name,
    #                 config=config_file
    #             )

    # ----------------------------------------------------------
    # PRE/POST-BUILD TASKS
    # ----------------------------------------------------------
    #
    # TODO: Generalize into a helper method

    for task in run_configs["build"]["pre"]:  # NOTE: Exact same for post-build

        print("-----------------------------------------------------------")

        # OS COMMAND TASK
        if task["task"].lower() == "os":
            log.debug(f"[TASK] build.pre.os ...")

            command_base = task.get("command", "")
            arguments = task.get("arguments", [])
            show_output = task.get("show_output", True)
            skip_on_fail = task.get("skip_on_fail", False)
            # expected_result = task.get("expected_result", {'status_code': 0})

            log.debug(f"Running local OS command: {command_base}")
            log.debug(f"   - Command: {command_base}")
            log.debug(f"   - Arguments: {arguments}")
            command_full = command_base + " " + " ".join(arguments)
            try:
                process = subprocess.Popen(command_full,
                                           shell=True,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           text=True)
                stdout, stderr = process.communicate()
            except subprocess.CalledProcessError as error:
                fail_out(f"build.pre.os - Failed running local OS command. Error: {error}")

            if process.returncode == 0:
                if task.get("show_output"):
                    print2(stdout.strip())
            else:
                msg = f"build.pre.os - Failed running local OS command. Error: {stderr.strip()}"
                if skip_on_fail:
                    warn_out(msg)
                else:
                    fail_out(msg)

        # REQUEST TASK
        elif task["task"].lower() == "request":
            log.debug(f"[TASK] build.pre.request ...")

            url = task.get("url", "")
            request_type = task.get("type", "get")
            headers = task.get("headers", {})
            parameters = task.get("parameters", {})
            skip_on_fail = task.get("skip_on_fail", False)
            # expected_result = task.get("expected_result", {'status_code': 200})

            return_content, _, success = yj_obj.rest.request(
                target=url,
                request_type=request_type,
                headers=headers,
                params=parameters,
                is_endpoint=False,
            )
            if not success:
                msg = f"build.pre.request - Error: Failed HTTP/S request: {url}"
                if not skip_on_fail:
                    fail_out(msg)
                else:
                    warn_out(msg)

            print2(return_content)

    # ----------------------------------------------------------
    # BUILD TASK
    # ----------------------------------------------------------
    # job_parameters = run_configs["build"]["parameters"]
    # job_name = run_configs["build"]["job"]
    # yj_obj.job.build_trigger(job_name=job_name, parameters=job_parameters)

    # ----------------------------------------------------------
    # LOGS TASK
    # ----------------------------------------------------------

    click.secho('success', fg='bright_green', bold=True)


# @log_to_history
# def upgrade(user: bool, proxy: str) -> None:
#     """TODO Docstring
#
#     Details: TODO
#
#     Args:
#         TODO
#     """
#     if not Package.install(user=user, proxy=proxy):
#         click.secho('failed to upgrade', fg='bright_red', bold=True)
#         sys.exit(1)
#     click.secho('successfully upgraded', fg='bright_green', bold=True)

# @log_to_history
# def remove() -> None:
#     """TODO Docstring
#
#     Details: TODO
#
#     Args:
#         TODO
#     """
#     if click.confirm('Are you sure you want to remove yojenkins?'):
#         Package.uninstall()
