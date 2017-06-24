import base64
import time
import json
import urllib.parse

import requests

import hub2labhook

from hub2labhook.utils import getenv


GITLAB_TIMEOUT = 30
API_VERSION = "/api/v4"


class GitlabClient(object):

    def __init__(self, endpoint=None, token=None):
        self.gitlab_token = getenv(token, "GITLAB_TOKEN")
        self.endpoint = getenv(endpoint, "GITLAB_API", "https://gitlab.com")
        self._headers = None
        self.host = self.endpoint

    def _url(self, path):
        return self.endpoint + API_VERSION + path

    @property
    def headers(self):
        if not self._headers:
            self._headers = {'Content-Type': 'application/json',
                             'User-Agent': "hub2lab: %s" % hub2labhook.__version__,
                             'PRIVATE-TOKEN': self.gitlab_token}
        return self._headers

    def get_project(self, project_id):
        path = self._url("/projects/%s" % project_id)
        resp = requests.get(path,
                            headers=self.headers, timeout=GITLAB_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def get_project_id(self, project_name=None):
        if isinstance(project_name, int):
            return project_name
        else:
            build_project = getenv(project_name, "GITLAB_REPO")
            namespace, name = build_project.split("/")
            project_path = "%s%%2f%s" % (namespace, name)
            project = self.get_project(project_path)
            return project['id']

    def set_variables(self, project_id, variables):
        path = self._url("/projects/%s/variables" % self.get_project_id(project_id))
        for key, value in variables.iteritems():
            key_path = path + "/%s" % key
            resp = requests.get(key_path)
            action = "post"
            if resp.status_code == 200:
                if resp.json()['value'] == value:
                    continue
                action = "put"
            body = {"key": key, "value": value}
            resp = getattr(requests, action)(path, data=json.dumps(body), headers=self.headers)
            resp.raise_for_status()

    def get_job(self, project_id, job_id):
        path = self._url("/projects/%s/jobs/%s" % (self.get_project_id(project_id), job_id))
        resp = requests.get(path, headers=self.headers, timeout=GITLAB_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def get_statuses(self, project_id, sha):
        path = self._url("/projects/%s/repository/commits/%s/statuses" % (self.get_project_id(project_id), sha))
        resp = requests.get(path, headers=self.headers, timeout=GITLAB_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def get_jobs(self, project_id, pipeline_id):
        path = self._url("/projects/%s/pipelines/%s/jobs" % (self.get_project_id(project_id), pipeline_id))
        resp = requests.get(path, headers=self.headers, timeout=GITLAB_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def get_pipeline_status(self, project_id, pipeline_id):
        path = self._url("/projects/%s/pipelines/%s" % (self.get_project_id(project_id), pipeline_id))
        resp = requests.get(path, headers=self.headers, timeout=GITLAB_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def get_namespace_id(self, namespace):
        path = self._url("/namespaces")
        params = {'search': namespace}
        resp = requests.get(path, headers=self.headers, params=params, timeout=GITLAB_TIMEOUT)
        resp.raise_for_status()
        return resp.json()[0]['id']

    def get_or_create_project(self, project_name, namespace=None):
        group_name = getenv(namespace, "FAILFASTCI_NAMESPACE", "failfast-ci")
        project_path = "%s%%2f%s" % (group_name, project_name)
        path = self._url("/projects/%s" % (project_path))
        resp = requests.get(path, headers=self.headers, timeout=GITLAB_TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
        group_id = self.get_namespace_id(group_name)
        path = self._url("/projects")
        body = {
            "name":  project_name,
            "namespace_id": group_id,
            "issues_enabled": False,
            "merge_requests_enabled": False,
            "jobs_enabled": True,
            "wiki_enabled": False,
            "snippets_enabled": False,
            "container_registry_enabled": False,
            "shared_runners_enabled": False,
            "public": True,
            "visibility_level": 20,
            "public_jobs": True,
            }
        resp = requests.post(path, data=json.dumps(body),
                             headers=self.headers, timeout=GITLAB_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def push_file(self, project_id, file_path,
                  file_content, branch, message,
                  force=True):
        branch_path = self._url("/projects/%s/repository/branches" % self.get_project_id(project_id))
        branch_body = {'branch': branch, 'ref': "_failfastci"}
        resp = requests.post(branch_path,
                             params=branch_body,
                             headers=self.headers, timeout=GITLAB_TIMEOUT)

        path = self._url("/projects/%s/repository/files/%s" % (self.get_project_id(project_id), urllib.parse.quote_plus(file_path)))
        body = {"file_path": file_path,
                "branch": branch,
                "encoding": "base64",
                "content": base64.b64encode(file_content).decode(),
                "commit_message": message}
        resp = requests.post(path, data=json.dumps(body), headers=self.headers, timeout=GITLAB_TIMEOUT)
        if resp.status_code == 400 or resp.status_code == 409:
            resp = requests.put(path, data=json.dumps(body), headers=self.headers, timeout=GITLAB_TIMEOUT)

        resp.raise_for_status()
        return resp.json()

    def delete_project(self, project_id):
        path = self._url("/projects/%s" % (self.get_project_id(project_id)))
        resp = requests.delete(path)
        resp.raise_for_status()
        return resp.json()

    def initialize_project(self, project_name, namespace=None):
        project = self.get_or_create_project(project_name, namespace)
        branch = "master"
        branch_path = self._url("/projects/%s/repository/branches/%s" % (project['id'], branch))
        resp = requests.get(branch_path, headers=self.headers, timeout=GITLAB_TIMEOUT)
        if resp.status_code == 404:
            time.sleep(2)
            self.push_file(project['id'],
                           file_path="README.md",
                           file_content=bytes(("# %s" % project_name).encode()),
                           branch="master",
                           message="init readme")
            time.sleep(2)
            resp = requests.put(branch_path + "/unprotect", headers=self.headers, timeout=GITLAB_TIMEOUT)
            resp.raise_for_status()
            branch_path = self._url("/projects/%s/repository/branches" % project['id'])
            branch_body = {'branch': "_failfastci", 'ref': "master"}
            resp = requests.post(branch_path,
                                 params=branch_body,
                                 headers=self.headers, timeout=GITLAB_TIMEOUT)

        return project

    def trigger_build(self, gitlab_project, variables={}, trigger_token=None, branch="master"):
        project_id = self.get_project_id(gitlab_project)
        project_branch = getenv(branch, "GITLAB_BRANCH")
        trigger_token = getenv(trigger_token, 'GITLAB_TRIGGER')

        body = {"token": trigger_token,
                "ref": project_branch,
                "variables": variables}

        path = self._url("/projects/%s/trigger/builds" % project_id)
        resp = requests.post(path,
                             data=json.dumps(body),
                             headers=self.headers,
                             timeout=GITLAB_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
