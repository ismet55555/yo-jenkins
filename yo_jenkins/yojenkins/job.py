"""Job class definition"""

import json
import logging
import re
from datetime import timedelta
from time import perf_counter
from typing import Dict, Tuple, Union
from urllib.parse import urlencode

import jenkins
import xmltodict

from yo_jenkins.monitor import JobMonitor
from yo_jenkins.utility import utility
from yo_jenkins.yojenkins.jenkins_item_classes import JenkinsItemClasses
from yo_jenkins.yojenkins.jenkins_item_config import JenkinsItemConfig

# Getting the logger reference
logger = logging.getLogger()


class Job():
    """TODO Job"""

    def __init__(self, REST, Folder, JenkinsSDK, Auth, Build) -> None:
        """Object constructor method, called at object creation

        Args:
            None

        Returns:
            None
        """
        self.REST = REST
        self.Folder = Folder
        self.JenkinsSDK = JenkinsSDK
        self.Auth = Auth
        self.Build = Build
        self.JM = JobMonitor(REST, Auth, self, Build)

        # Recursive search results
        self.search_results = []
        self.search_items_count = 0

    def __recursive_search(self, search_pattern: str, search_list: list, level: int, fullname: bool = True) -> None:
        """Recursive search method for jobs

        Details: Matched pattern findings are storred in the object: `self.search_results`

        Args:
            search_pattern : REGEX pattern to match for each item
            search_list    : List of items
            level          : Current recursion level
            fullname       : Search the entire path of the item, not just the item name

        Returns:
            None
        """
        # Current directory level
        level += 1

        # Loop through all sub-folders
        for list_item in search_list:

            # Check if it is not a job
            if list_item['_class'] in JenkinsItemClasses.JOB.value['class_type']:

                # Get fullname, else get name
                if fullname:
                    dict_key = "fullname" if "fullname" in list_item else "name"
                else:
                    dict_key = 'name'

                # Match the regex pattern
                try:
                    if re.search(search_pattern, list_item[dict_key], re.IGNORECASE):
                        self.search_results.append(list_item)
                except re.error as error:
                    logger.debug(
                        f'Error while applying REGEX pattern "{search_pattern}" to "{list_item[dict_key]}". Exception: {error}'
                    )
                    break

            # Count items searched for record
            self.search_items_count += 1

            # Check if it is a folder, if it is, keep looking
            if 'jobs' not in list_item:
                continue

            # Keep searching all sub-items for this item. Call itself for some recursion fun
            self.__recursive_search(search_pattern, list_item['jobs'], level, fullname)

    def search(self,
               search_pattern: str,
               folder_name: str = '',
               folder_url: str = '',
               folder_depth: int = 4,
               fullname: bool = True) -> Tuple[list, list]:
        """TODO Docstring

        Args:
            arg 1 : DESCRIPTION
            arg 2 : DESCRIPTION

        Returns:
            TODO
        """
        # Finding the job by REGEX pattern
        # NOTE:
        #   - Criteria of jobs is that jobs do not have any sub-folders, only views and jobs

        # Start a timer to time the search
        start_time = perf_counter()

        logger.debug(f'Job search pattern: {search_pattern}')

        # Get all the jobs
        if folder_name or folder_url:
            # Only recursively search the specified folder name
            logger.debug(f'Searching jobs in sub-folder "{folder_name if folder_name else folder_url}"')
            logger.debug('Folder depth does not apply. Only looking in this specific folder for job')
            items = self.Folder.item_list(folder_name=folder_name, folder_url=folder_url)[0]
        else:
            # Search entire Jenkins
            logger.debug(f'Searching jobs in ALL Jenkins. Folder depth: "{folder_depth}"')
            try:
                items = self.JenkinsSDK.get_all_jobs(folder_depth=folder_depth)
            except jenkins.JenkinsException as error:
                error_no_html = error.args[0].split("\n")[0]
                logger.debug(f'Error while getting all items. Exception: {error_no_html}')

                # TODO: Catch authentication error "[401]: Unauthorized"
                return [], []

        # Search for any matching folders ("jobs")
        self.search_results = []
        self.search_items_count = 0
        self.__recursive_search(search_pattern=search_pattern, search_list=items, level=0, fullname=fullname)

        # Remove duplicates from list
        logger.debug('Removing duplicates if needed ...')
        self.search_results = [i for n, i in enumerate(self.search_results) if i not in self.search_results[n + 1:]]

        # Getting only the URLs of the stages
        job_search_results_list = [r['url'] for r in self.search_results]

        # Output search stats
        logger.debug(
            f'Searched jobs: {self.search_items_count}. Search time: {perf_counter() - start_time:.3f} seconds')

        return self.search_results, job_search_results_list

    def info(self, job_name: str = '', job_url: str = '') -> Dict:
        """TODO Docstring

        Args:
            TODO

        Returns:
            TODO
        """
        if not job_name and not job_url:
            logger.debug('Failed to get job information. No job name or job url received')
            return {}

        if job_name and not job_url:
            job_url = utility.name_to_url(self.REST.get_server_url(), job_name)

        logger.debug(f'Job url passed: {job_url}')
        job_info, _, success = self.REST.request(f'{job_url.strip("/")}/api/json', 'get', is_endpoint=False)
        if not success:
            logger.debug(f'Failed to find job info: {job_url}')
            return {}

        # Check if found item type/class
        if job_info['_class'] not in JenkinsItemClasses.JOB.value['class_type']:
            logger.debug(f'Failed to match type/class. This item is "{job_info["_class"]}"')
            return {}

        if 'url' in job_info:
            job_info['fullName'] = utility.url_to_name(job_info['url'])
            job_info['jobUrl'] = utility.build_url_to_other_url(job_info['url'], target_url='job')
            job_info['jobFullName'] = utility.url_to_name(job_info['jobUrl'])
            job_info['folderUrl'] = utility.build_url_to_other_url(job_info['url'], target_url='folder')
            job_info['folderFullName'] = utility.url_to_name(job_info['folderUrl'])
            job_info['serverURL'] = utility.item_url_to_server_url(job_info['url'])
            job_info['serverDomain'] = utility.item_url_to_server_url(job_info['url'], False)

            job_info[
                'folderFullName'] = 'Base Folder' if not job_info['folderFullName'] else job_info['folderFullName']

        return job_info

    def build_list(self, job_name: str = '', job_url: str = '') -> Tuple[list, list]:
        """TODO Docstring

        Args:
            TODO

        Returns:
            TODO
        """
        # Get the job information
        job_info = self.info(job_name=job_name, job_url=job_url)
        if not job_info:
            return [], []

        # Get all the past builds
        build_list, build_url_list = utility.item_subitem_list(
            item_info=job_info,
            get_key_info='url',
            item_type=JenkinsItemClasses.BUILD.value['item_type'],
            item_class_list=JenkinsItemClasses.BUILD.value['class_type'])

        return build_list, build_url_list

    def build_next_number(self, job_name: str = '', job_url: str = '') -> Union[int, None]:
        """TODO Docstring

        Args:
            TODO

        Returns:
            TODO
        """
        # Get the job information
        job_info = self.info(job_name=job_name, job_url=job_url)
        if not job_info:
            return None

        # TODO: Check if nextBuildNumber is even part of the info

        return job_info['nextBuildNumber']

    def build_last_number(self, job_name: str = '', job_url: str = '', job_info: dict = {}) -> int:
        """TODO Docstring

        Args:
            TODO

        Returns:
            TODO
        """
        # TODO: Return a url of the build instead just the number

        # Get the job information
        if not job_info:
            # If the job info is not passed, request it from server
            job_info = self.info(job_name=job_name, job_url=job_url)
            if not job_info:
                return 0

        if 'lastBuild' not in job_info:
            logger.debug('Failed to find "lastBuild" key in job info')
            return 0
        if 'number' not in job_info['lastBuild']:
            logger.debug('Failed to find "number" key in "lastBuild" section of job info')
            return 0

        return job_info['lastBuild']['number']

    def build_set_next_number(self, build_number: int, job_name: str = '', job_url: str = '') -> Union[int, None]:
        """TODO Docstring

        Args:
            TODO

        Returns:
            TODO
        """
        if not job_name and not job_url:
            logger.debug('Failed to set job next build number. No job name or job url received')
            return None
        if job_url and not job_name:
            job_name = utility.url_to_name(url=job_url)
        # Format name
        job_name = utility.format_name(name=job_name)

        logger.debug(f'Setting next build number for job "{job_name}" to {build_number} ...')

        try:
            # TODO: Use requests instead of jenkins-python
            response = self.JenkinsSDK.set_next_build_number(job_name, build_number)
        except jenkins.JenkinsException as error:
            error_no_html = error.args[0].split("\n")[0]
            logger.debug(
                f'Failed to set next build number for job "{job_name}" to {build_number}. Exception: {error_no_html}')
            return None

        return build_number

    def build_number_exist(self,
                           build_number: int,
                           job_info: dict,
                           job_name: str = '',
                           job_url: str = '') -> Union[bool, None]:
        """TODO Docstring

        Args:
            TODO

        Returns:
            TODO
        """
        if not job_info:
            # Getting job information
            job_info = self.info(job_name=job_name, job_url=job_url)
            if not job_info:
                logger.debug(f'Failed to find job "{job_name if job_name else job_url}"')
                return None

        if 'builds' not in job_info:
            logger.debug('Failed to get build list from job. "builds" key missing in job information')
            logger.debug(f'Job info: {job_info}')
            return None

        # Iterate through all listed builds
        for build in job_info['builds']:
            if build_number == build['number']:
                return True

        return False

    def build_trigger(self, job_name: str = '', job_url: str = '', paramters: Dict = {}, token: str = '') -> int:
        """TODO Docstring

        Args:
            TODO

        Returns:
            TODO
        """
        # NOTE: The jenkins-python module build_job() does not work. Using requests instead

        if not job_name and not job_url:
            logger.debug('Failed to get trigger job build. No job name or job url received')
            return 0

        logger.debug(f'Job reference passed: {job_name if job_name else job_url}')

        # Need both the job name and the job URL
        if job_url and not job_name:
            job_name = utility.url_to_name(url=job_url)
        elif job_name and not job_url:
            # TODO: Use requests instead of Jenkins SDK
            job_url = self.JenkinsSDK.build_job_url(name=job_name).strip('build')
        job_url = job_url.strip('/')

        next_build_number = self.build_next_number(job_name=job_name, job_url=job_url)
        logger.debug(f'Triggering job "{job_url}", build {next_build_number} ...')

        if paramters:
            # Use the paramters passed
            logger.debug(f'Triggering with job paramters: {paramters}')
            post_url = f'{job_url}/buildWithParameters?{urlencode(paramters)}'
        else:
            # No paramters passed
            post_url = f'{job_url}/build'

        logger.debug(f'POST url: {post_url}')

        # Posting to Jenkins
        return_headers = self.REST.request(post_url, 'post', is_endpoint=False)[1]

        # Parse the queue location of the build
        if return_headers:
            build_queue_url = return_headers['Location']
            if build_queue_url.endswith('/'):
                queue_location = build_queue_url[:-1]
            parts = queue_location.split('/')
            build_queue_number = int(parts[-1])
            logger.debug(f'Build queue URL: {queue_location}')
            logger.debug(f'Build queue ID: {build_queue_number}')
        else:
            return 0

        return build_queue_number

    def wipeout_workspace(self, job_name: str = '', job_url: str = '') -> bool:
        """TODO Docstring

        Args:
            TODO

        Returns:
            TODO
        """
        # TODO
        pass

    def queue_info(self, build_queue_number: int = 0, build_queue_url: str = '') -> Dict:
        """TODO Docstring

        Args:
            TODO

        Returns:
            TODO
        """
        logger.debug(f'Getting information for build queue "{build_queue_number}" ...')

        # Make the request URL
        if build_queue_number:
            endpoint = f'queue/item/{build_queue_number}/api/json'
        elif build_queue_url:
            endpoint = f'{build_queue_url}api/json'
        else:
            logger.error('No build queue number or build queue url passed')
            return {}
        queue_info = self.REST.request(endpoint, 'get', is_endpoint=True)[0]

        # Adding additional parameters
        if queue_info:
            queue_info['isQueuedItem'] = True
            queue_info['fullUrl'] = self.REST.get_server_url().strip('/') + '/' + queue_info['url']
            queue_info['jobUrl'] = queue_info['task']['url']
            queue_info['jobFullName'] = utility.url_to_name(queue_info['jobUrl'])
            queue_info['folderUrl'] = utility.build_url_to_other_url(queue_info['fullUrl'], target_url='folder')
            queue_info['folderFullName'] = utility.url_to_name(queue_info['folderUrl'])
            queue_info['serverURL'] = utility.item_url_to_server_url(queue_info['url'])
            queue_info['serverDomain'] = utility.item_url_to_server_url(queue_info['url'], False)

        return queue_info

    def in_queue_check(self, job_name: str = '', job_url: str = '') -> Tuple[dict, int]:
        """TODO Docstring

        Args:
            TODO

        Returns:
            TODO
        """
        if not job_name and not job_url:
            logger.debug('Failed to get job information. No job name or job url received')
            return {}

        # Requesting all queue and searching queue (NOTE: Could use Server object)
        queue_all = self.REST.request('queue/api/json', 'get')[0]
        logger.debug(f"Number of queued items: {len(queue_all['items'])}")
        queue_matches = utility.queue_find(queue_all, job_name=job_name, job_url=job_url)
        if not queue_matches:
            return {}, 0
        queue_info = queue_matches[0]

        # Adding additional parameters
        if queue_info:
            queue_info['inQueueSinceFormatted'] = str(timedelta(seconds=queue_info['inQueueSince'] / 1000.0))[:-3]
            queue_info['fullUrl'] = self.REST.get_server_url() + '/' + queue_info['url']
            queue_info['jobUrl'] = queue_info['task']['url']
            queue_info['jobFullName'] = utility.url_to_name(queue_info['jobUrl'])
            queue_info['folderUrl'] = utility.build_url_to_other_url(queue_info['fullUrl'], target_url='folder')
            queue_info['folderFullName'] = utility.url_to_name(queue_info['folderUrl'])
            queue_info['serverURL'] = utility.item_url_to_server_url(queue_info['fullUrl'])
            queue_info['serverDomain'] = utility.item_url_to_server_url(queue_info['fullUrl'], False)

        return queue_info, queue_info['id']

    def queue_abort(self, build_queue_number: int) -> bool:
        """TODO Docstring

        Args:
            TODO

        Returns:
            TODO
        """
        logger.debug(f'Aborting build queue "{build_queue_number}" ...')

        if not build_queue_number:
            logger.error('No build queue number passed')
            return False

        # Make the request URL
        endpoint = f'queue/cancelItem?id={build_queue_number}'
        return_content = self.REST.request(endpoint, 'post', is_endpoint=True)[0]

        if not return_content:
            logger.error(
                'Failed to abort build queue. Specified build queue number may be wrong or build may have already started'
            )
            logger.error('The following jobs are currently in queue:')
            queue_list = self.in_queue_check()
            for i, queue_item in enumerate(queue_list):
                logger.error(f'  {i+1}. Queue ID: {queue_item["id"]} - Job URL: {queue_item["task"]["url"]}')

            return False

        return True

    def browser_open(self, job_name: str = '', job_url: str = '') -> bool:
        """TODO Docstring

        Args:
            TODO

        Returns:
            TODO
        """
        if not job_name and not job_url:
            logger.debug('Failed to get job information. No job name or job url received')
            return False

        if job_url:
            job_url = job_url.strip('/')
        else:
            job_url = utility.name_to_url(self.REST.get_server_url(), job_name)

        logger.debug(f'Opening in web browser: "{job_url}" ...')
        success = utility.browser_open(url=job_url)
        logger.debug('Successfully opened in web browser' if success else 'Failed to open in web browser')
        return success

    def config(self,
               filepath: str = '',
               job_name: str = '',
               job_url: str = '',
               opt_json: bool = False,
               opt_yaml: bool = False,
               opt_toml: bool = False) -> Tuple[str, bool]:
        """Get the folder XML configuration (config.xml)

        Args:
            filepath    : If defined, store fetched data in this file
            job_name    : Job name to get configurations
            folder_url  : Job URL to get configurations

        Returns:
            Folder config.xml contents
            True if configuration written to file, else False
        """
        if not job_name and not job_url:
            logger.debug('Failed to get job information. No job name or job url received')
            return '', False

        if job_url:
            job_url = job_url.strip('/')
        else:
            job_url = utility.name_to_url(self.REST.get_server_url(), job_name)

        logger.debug(f'Fetching XML configurations for job: "{job_url}" ...')
        return_content, _, success = self.REST.request(f'{job_url.strip("/")}/config.xml',
                                                       'get',
                                                       json_content=False,
                                                       is_endpoint=False)
        logger.debug('Successfully fetched XML configurations' if success else 'Failed to fetch XML configurations')

        if filepath:
            write_success = utility.write_xml_to_file(return_content, filepath, opt_json, opt_yaml, opt_toml)
            if not write_success:
                return "", False

        return return_content, True

    def disable(self, job_name: str = '', job_url: str = '') -> bool:
        """TODO Docstring

        Args:
            TODO

        Returns:
            TODO
        """
        if not job_name and not job_url:
            logger.debug('Failed to get job information. No job name or job url received')
            return False

        if job_url:
            job_url = job_url.strip('/')
        else:
            job_url = utility.name_to_url(self.REST.get_server_url(), job_name)

        logger.debug(f'Disabling job: "{job_url}" ...')
        success = self.REST.request(f'{job_url.strip("/")}/disable', 'post', is_endpoint=False)[2]
        logger.debug('Successfully disabled job' if success else 'Failed to disable job')
        return success

    def enable(self, job_name: str = '', job_url: str = '') -> bool:
        """TODO Docstring

        Args:
            TODO

        Returns:
            TODO
        """
        if not job_name and not job_url:
            logger.debug('Failed to get job information. No job name or job url received')
            return False

        if job_url:
            job_url = job_url.strip('/')
        else:
            job_url = utility.name_to_url(self.REST.get_server_url(), job_name)

        logger.debug(f'Enabling job: "{job_url}" ...')
        success = self.REST.request(f'{job_url.strip("/")}/enable', 'post', is_endpoint=False)[2]
        logger.debug('Successfully enabled job' if success else 'Failed to enable job')
        return success

    def rename(self, new_name: str, job_name: str = '', job_url: str = '') -> bool:
        """TODO Docstring

        Args:
            TODO

        Returns:
            TODO
        """
        if not job_name and not job_url:
            logger.debug('Failed to get job information. No job name or job url received')
            return False

        if job_url:
            job_url = job_url.strip('/')
        else:
            job_url = utility.name_to_url(self.REST.get_server_url(), job_name)

        if not new_name:
            logger.debug('New job name is a blank')
            return False
        if utility.has_special_char(new_name):
            return False

        logger.debug(f'Renaming job: "{job_url}" ...')
        success = self.REST.request(f'{job_url.strip("/")}/doRename?newName={new_name}', 'post', is_endpoint=False)[2]
        logger.debug('Successfully renamed job' if success else 'Failed to rename job')
        return success

    def delete(self, job_name: str = '', job_url: str = '') -> bool:
        """TODO Docstring

        Args:
            TODO

        Returns:
            TODO
        """
        if not job_name and not job_url:
            logger.debug('Failed to get job information. No job name or job url received')
            return False

        if job_url:
            job_url = job_url.strip('/')
        else:
            job_url = utility.name_to_url(self.REST.get_server_url(), job_name)

        logger.debug(f'Deleting job: "{job_url}" ...')
        success = self.REST.request(f'{job_url.strip("/")}/doDelete', 'post', is_endpoint=False)[2]
        logger.debug('Successfully deleted job' if success else 'Failed to delete job')
        return success

    def wipe_workspace(self, job_name: str = '', job_url: str = '') -> bool:
        """TODO Docstring

        Args:
            TODO

        Returns:
            TODO
        """
        if not job_name and not job_url:
            logger.debug('Failed to get job information. No job name or job url received')
            return False

        if job_url:
            job_url = job_url.strip('/')
        else:
            job_url = utility.name_to_url(self.REST.get_server_url(), job_name)

        logger.debug(f'Wiping workspace for job: "{job_url}" ...')
        success = self.REST.request(f'{job_url.strip("/")}/doWipeOutWorkspace', 'post', is_endpoint=False)[2]
        logger.debug('Successfully wiped job workspace' if success else 'Failed to wipe job workspace')
        return success

    def monitor(self, job_name: str = '', job_url: str = '', sound: bool = False) -> bool:
        """TODO Docstring

        Args:
            TODO

        Returns:
            TODO
        """
        if not job_name and not job_url:
            logger.debug('Failed to get job information. No job name or job url received')
            return False

        if job_url:
            job_url = job_url.strip('/')
        else:
            job_url = utility.name_to_url(self.REST.get_server_url(), job_name)

        logger.debug(f'Starting monitor for: "{job_url}" ...')
        success = self.JM.monitor_start(job_url=job_url, sound=sound)
        if success:
            logger.debug('Successfully opened monitor')
        else:
            logger.debug('Failed to open monitor for build')
        return success

    def create(self,
               name: str,
               folder_name: str = '',
               folder_url: str = '',
               config_file: str = 'config.xml',
               config_is_json: bool = False) -> bool:
        """TODO Docstring

        Args:
            TODO

        Returns:
            TODO
        """
        if not folder_name and not folder_url:
            logger.debug('Failed to get folder information. No folder name or folder url received')
            return False

        if folder_url:
            folder_url = folder_url.strip('/')
        else:
            folder_url = utility.name_to_url(self.REST.get_server_url(), folder_name)

        if not name:
            logger.debug('Item name is a blank')
            return False
        if utility.has_special_char(name):
            return False

        # Check if job already exists
        if utility.item_exists_in_folder(name, folder_url, "job", self.REST):
            return False

        if config_file:
            # Use job config from file
            logger.debug(f'Opening and reading file: {config_file} ...')
            try:
                open_file = open(config_file, 'rb')
                job_config = open_file.read()
            except (OSError, IOError, PermissionError) as error:
                logger.debug(f'Failed to open and read file. Exception: {error}')
                return False

            if config_is_json:
                logger.debug('Converting the specified JSON file to XML format ...')
                try:
                    job_config = xmltodict.unparse(json.loads(job_config))
                except ValueError as error:
                    logger.debug(f'Failed to convert the specified JSON file to XML format. Exception: {error}')
                    return False
        else:
            # Use blank job config template
            job_config = JenkinsItemConfig.JOB.value['blank']

        logger.debug(f'Creating job "{name}" within folder "{folder_url}" "...')
        endpoint = f'createItem?name={name}'
        headers = {'Content-Type': 'application/xml; charset=utf-8'}
        _, _, success = self.REST.request(f'{folder_url.strip("/")}/{endpoint}',
                                          'post',
                                          data=job_config.encode('utf-8'),
                                          headers=headers,
                                          is_endpoint=False)
        logger.debug(f'Successfully created item "{name}"' if success else f'Failed to create item "{name}"')

        try:
            open_file.close()
        except (OSError, IOError):
            pass

        return success