"""
Acquire runtime configuration from environment variables (etc).
"""

import os


def getenv(name, default=None, convert=str):
    """
    Fetch variables from environment and convert to given type.

    Python's `os.getenv` returns string and requires string default.
    This allows for varying types to be interpolated from the environment.
    """

    # because os.getenv requires string default.
    internal_default = "(none)"
    val = os.getenv(name, internal_default)

    if val == internal_default:
        return default

    if callable(convert):
        return convert(val)

    return val


def envbool(value: str):
    return value and (value.lower() in ('1', 'true'))


GITLAB_TIMEOUT = 30

APP_ENVIRON = getenv("APP_ENV", "development")

# Events from GitLab hooks will be authenticated with this token.
GITLAB_SECRET_TOKEN_DEFAULT = "e19c1283c925b3206685ff522acfe3e6"
GITLAB_SECRET_TOKEN = getenv("GITLAB_TOKEN", GITLAB_SECRET_TOKEN_DEFAULT)

GITLAB_API = getenv("GITLAB_API", "https://gitlab.com")
GITLAB_REPO = getenv("GITLAB_REPO", None)
GITLAB_BRANCH = getenv("GITLAB_BRANCH", None)
GITLAB_TRIGGER = getenv("GITLAB_TRIGGER", None)
GITLAB_USER = getenv("GITLAB_USER", None)
GITLAB_ENABLE_JOBS = True  # without this, CI is moot.

GITLAB_ENABLE_SHARED_RUNNERS = getenv("GITLAB_SHARED_RUNNERS", default=False,
                                      convert=envbool)

GITLAB_ENABLE_CONTAINER_REGISTRY = getenv("GITLAB_CONTAINER_REGISTRY",
                                          default=False, convert=envbool)

GITLAB_ENABLE_WIKI = getenv("GITLAB_WIKI", default=False, convert=envbool)
GITLAB_ENABLE_SNIPPETS = getenv("GITLAB_SNIPPETS", default=False,
                                convert=envbool)

GITLAB_ENABLE_MERGE_REQUESTS = getenv("GITLAB_MERGE_REQUESTS", default=False,
                                      convert=envbool)
GITLAB_ENABLE_ISSUES = getenv("GITLAB_ISSUES", default=False, convert=envbool)

GITLAB_REPO_PRIVACY = getenv("GITLAB_REPO_PRIVACY", default="internal")

if GITLAB_REPO_PRIVACY not in ("private", "internal", "public"):
    GITLAB_REPO_PRIVACY = "private"

GITHUB_CONTEXT = getenv("GITHUB_CONTEXT", "gitlab-ci")
GITHUB_INTEGRATION_ID = getenv("GITHUB_INTEGRATION_ID", "743")
GITHUB_INSTALLATION_ID = getenv("GITHUB_INSTALLATION_ID", "3709")
GITHUB_SECRET_TOKEN = getenv("GITHUB_SECRET_TOKEN", None)

FAILFASTCI_NAMESPACE = getenv("FAILFASTCI_NAMESPACE", "failfast-ci")
FAILFASTCI_API = getenv("FAILFAST_CI_API", "https://jobs.failfast-ci.io")

BUILD_PULL_REQUEST = getenv("BUILD_PULL_REQUEST", "true")
BUILD_PUSH = getenv("BUILD_PUSH", "false")


class FailFastConfig(object):
    """
    """
    def __init__(self, defaults=None):
        self.project_settings = {
                    'privacy': GITLAB_REPO_PRIVACY,
                    'namespace': FAILFASTCI_NAMESPACE,
                    'robot-user': GITLAB_USER,
                    'branch': GITLAB_BRANCH,    # @TODO(ant31): Remove this key
                    'trigger': GITLAB_TRIGGER,  # @TODO(ant31): Remove this key

                    'enabled': {
                        'shared_runners': GITLAB_ENABLE_SHARED_RUNNERS,
                        'container_registry': GITLAB_ENABLE_CONTAINER_REGISTRY,
                        'wiki': GITLAB_ENABLE_WIKI,
                        'snippets': GITLAB_ENABLE_SNIPPETS,
                        'issues': GITLAB_ENABLE_ISSUES,
                        'merge_requests': GITLAB_ENABLE_MERGE_REQUESTS,
                    }
                }

        self.settings = {
            'failfast': {
                'env': APP_ENVIRON,
                'host': FAILFASTCI_API,
                'build': {
                    'push': ['master'],  # list branches (regexp) to trigger builds on push events
                    'pr': ['*'],         # list branches (regexp) to trigger builds on PR events
                    'tags': ['*']        # list branches (regexp) to trigger builds on new tags
                }
            },

            'github': {
                'context': GITHUB_CONTEXT,
                'installation_id': GITHUB_INSTALLATION_ID,
                'secret_token': GITHUB_SECRET_TOKEN,
                'integration_id': GITHUB_INTEGRATION_ID,
            },
            'gitlab': {
                'timeout': GITLAB_TIMEOUT,
                'secret_token': GITLAB_SECRET_TOKEN,
                'host': GITLAB_API,

                'project-defaults': self.project_settings,
                }
            }

        if defaults:
            self.load(defaults)

    def load(self, settings):
        self.settings.update(settings)


FFCONFIG = FailFastConfig()