#!/usr/bin/env python3

import logging
from pprint import pprint
from typing import Dict, List, Tuple, Type

import jenkins

# Getting the logger reference
logger = logging.getLogger()


class Server():
    """TODO Server"""

    def __init__(self, REST, Auth) -> None:
        """Object constructor method, called at object creation

        Args:
            None

        Returns:
            None
        """
        self.REST = REST
        self.Auth = Auth

        self.server_base_url = self.Auth.jenkins_profile['jenkins_server_url']


    def info(self) -> Dict:
        """Get the server information

        Details: Targeting the server that is specified in the selected profile

        Args:
            None

        Returns:
            Server information
        """
        return self.REST.request('api/json', 'get')[0]


    def user_info(self) -> Dict:
        """Get user information

        Details: Targeting the user that is specified in the selected profile

        Args:
            None

        Returns:
            User information
        """
        return self.REST.request('me/api/json', 'get')[0]


    def queue_info(self) -> Dict:
        """Get all the jobs stuck in the server queue

        (Potentially move to jobs or build section)

        Args:
            None

        Returns:
            Server queue information
        """
        # TODO: Combine with server_queue_list adding a list argument

        logger.debug(f'Requesting build queue info for "{self.server_base_url}" ...')

        # Making the request
        return_content = self.REST.request('queue/api/json', 'get')[0]
        if not return_content:
            logger.debug('Failed to get server queue info. Check access and permissions for this endpoint')
        return return_content


    def queue_list(self) -> List[str]:
        """Get all list of all the jobs stuck in the server queue

        (Potentially move to jobs or build section)

        Args:
            None

        Returns:
            List of urls of jobs stuck in server queue
        """
        queue_info = self.queue_info()

        queue_list = []
        queue_job_url_list = []
        for queue_item in queue_info['items']:
            queue_list.append(queue_item)
            if 'url' in queue_item['task']:
                queue_job_url_list.append(queue_item['task']['url'])

        return queue_list


    def plugin_list(self) -> Tuple[list, list]:
        """Get the list of plugins installed on the server

        Args:
            None

        Returns:
            List of plugins, information list and URL list
        """
        logger.debug(f'Getting all installed server plugins for "{self.server_base_url}" ...')

        try:
            # TODO: Replace with REST call
            plugin_info = self.J.get_plugins()
        except jenkins.JenkinsException as e:
            error_no_html = e.args[0].split("\n")[0]
            logger.debug(f'Failed to get server plugin information. Exception: {error_no_html}')
            return [], []

        pprint(plugin_info)

        plugin_info_list = ['TODO']

        return plugin_info, plugin_info_list

