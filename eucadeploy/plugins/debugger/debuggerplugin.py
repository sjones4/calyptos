# stevedore/example/base.py
import abc
import fabric
from fabric.colors import red, green, cyan
from fabric.decorators import task
from fabric.operations import run
from fabric.state import env
from fabric.tasks import execute
import six


@six.add_metaclass(abc.ABCMeta)
class DebuggerPlugin(object):
    """Base class for example plugin used in the tutorial.
    """

    def __init__(self, component_deployer):
        self.passed = 0
        self.failed = 0
        self.message_style = "[{0: <20}] {1}"
        self.name = self.__class__.__name__
        self.component_deployer = component_deployer
        self.environment = self.component_deployer.read_environment()
        self.roles = self.component_deployer.get_roles()
        print cyan(self.message_style.format('DEBUG STARTING', self.name))

    def __del__(self):
        self.report()

    def success(self, message):
        self.passed +=1
        print green(self.message_style.format('DEBUG PASSED', message))

    def failure(self, message):
        self.failed +=1
        print red(self.message_style.format('DEBUG FAILED', message))

    def report(self):
        text_color = red
        if self.failed == 0:
            text_color = cyan
        print text_color(self.message_style.format('DEBUG RESULTS',
                                             "Name: {0} Passed: "
                                             "{1} Failed: {2}  ".format(
                                                 self.name,
                                                 str(self.passed),
                                                 str(self.failed))))

    @task
    def run_command_task(command, user='root', password='foobar'):
        env.user = user
        env.password = password
        env.parallel = True
        return run(command)

    def run_command_on_hosts(self, command, hosts, host=None):
        return execute(self.run_command_task, command=command, hosts=hosts)

    def run_command_on_host(self, command, host):
        return execute(self.run_command_task, command=command, host=host)[host]

    def debug(self):
        """Format the data and return unicode text.

        :param data: A dictionary with string keys and simple types as
                     values.
        :type data: dict(str:?)
        :returns: Iterable producing the formatted text.
        """