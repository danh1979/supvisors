#!/usr/bin/python
#-*- coding: utf-8 -*-

# ======================================================================
# Copyright 2016 Julien LE CLEACH
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ======================================================================

import os

from supervisor.http import NOT_DONE_YET
from supervisor.options import split_namespec
from supervisor.xmlrpc import Faults, RPCError

from supvisors.initializer import Supvisors
from supvisors.ttypes import ApplicationStates, DeploymentStrategies, SupvisorsStates
from supvisors.utils import supvisors_short_cuts

# get Supvisors version from file
here = os.path.abspath(os.path.dirname(__file__))
version_txt = os.path.join(here, 'version.txt')
API_VERSION = open(version_txt).read().split('=')[1].strip()


class RPCInterface(object):
    """ This class holds the XML-RPC extension provided by **Supvisors**. """

    def __init__(self, supervisord):
        # create a new Supvisors instance
        self.supvisors = Supvisors(supervisord)
        supvisors_short_cuts(self, ['context', 'fsm', 'info_source', 'logger', 'starter', 'stopper'])

    # RPC Status methods
    def get_api_version(self):
        """ Return the version of the RPC API used by **Supvisors**.

        *@return* ``str``: the version id.
        """
        return API_VERSION

    def get_supvisors_state(self):
        """ Return the state of **Supvisors**.

        *@return* ``dict``: the state of **Supvisors** as an integer and a string.
        """
        return self.fsm.serial()

    def get_master_address(self):
        """ Get the address of the **Supvisors** Master.

        *@return* ``str``: the IPv4 address or host name.
        """
        return self.context.master_address

    def get_all_addresses_info(self):
        """ Get information about all **Supvisors** instances.

        *@return* ``list(dict)``: a list of structures containing data about all **Supvisors** instances.
        """
        return [self.get_address_info(address_name) for address_name in self.context.addresses.keys()]

    def get_address_info(self, address_name):
        """ Get information about the **Supvisors** instance running on the host named address_name.

        *@param* ``str address_name``: the address name where the Supervisor daemon is running.

        *@throws* ``RPCError``: with code ``Faults.BAD_ADDRESS`` if address name is unknown to **Supvisors**.

        *@return* ``dict``: a structure containing data about the **Supvisors** instance.
        """
        try:
            status = self.context.addresses[address_name]
        except KeyError:
            raise RPCError(Faults.BAD_ADDRESS, 'address {} unknown in Supvisors'.format(address_name))
        return status.serial()

    def get_all_applications_info(self):
        """ Get information about all applications managed in **Supvisors**.

        *@throws* ``RPCError``: with code ``Faults.BAD_SUPVISORS_STATE`` if **Supvisors** is still in ``INITIALIZATION`` state.

        *@return* ``list(dict)``: a list of structures containing data about all applications.
        """
        self._check_from_deployment()
        return [self.get_application_info(application_name) for application_name in self.context.applications.keys()]

    def get_application_info(self, application_name):
        """ Get information about an application named application_name.

        *@param* ``str application_name``: the name of the application.

        *@throws* ``RPCError``:

            * with code ``Faults.BAD_SUPVISORS_STATE`` if **Supvisors** is still in ``INITIALIZATION`` state,
            * with code ``Faults.BAD_NAME`` if application_name is unknown to **Supvisors**.

        *@return* ``dict``: a structure containing data about the application.
        """
        self._check_from_deployment()
        return self._get_application(application_name).serial()

    def get_all_process_info(self):
        """ Get information about all processes.

        *@throws* ``RPCError``: with code ``Faults.BAD_SUPVISORS_STATE`` if **Supvisors** is still in state ``INITIALIZATION``,

        *@return* ``list(dict)``: a list of structures containing data about the processes.
        """
        self._check_from_deployment()
        return [process.serial() for process in self.context.processes.values()]

    def get_process_info(self, namespec):
        """ Get information about a process named namespec.
        It just complements ``supervisor.getProcessInfo`` by telling where the process is running.

        *@param* ``str namespec``: the process namespec (``name``, ``group:name``, or ``group:*``).

        *@throws* ``RPCError``:

            * with code ``Faults.BAD_SUPVISORS_STATE`` if **Supvisors** is still in state ``INITIALIZATION``,
            * with code ``Faults.BAD_NAME`` if namespec is unknown to **Supvisors**.

        *@return* ``list(dict)``: a list of structures containing data about the processes.
        """
        self._check_from_deployment()
        application, process = self._get_application_process(namespec)
        if process:
            return [process.serial()]
        return [proc.serial() for proc in application.processes.values()]

    def get_process_rules(self, namespec):
        """ Get the rules used to start / stop the process named namespec.

        *@param* ``str namespec``: the process namespec (``name``, ``group:name``, or ``group:*``).

        *@throws* ``RPCError``:

            * with code ``Faults.BAD_SUPVISORS_STATE`` if **Supvisors** is still in state ``INITIALIZATION``,
            * with code ``Faults.BAD_NAME`` if namespec is unknown to **Supvisors**.

        *@return* ``list(dict)``: a list of structures containing the rules.
        """
        self._check_from_deployment()
        application, process = self._get_application_process(namespec)
        if process:
            return [self._get_internal_process_rules(process)]
        return [self._get_internal_process_rules(proc) for proc in application.processes.values()]

    def get_conflicts(self):
        """ Get the conflicting processes.

        *@throws* ``RPCError``: with code ``Faults.BAD_SUPVISORS_STATE`` if **Supvisors** is still in state ``INITIALIZATION``,

        *@return* ``list(dict)``: a list of structures containing data about the conflicting processes.
        """
        self._check_from_deployment()
        return [process.serial() for application in self.context.applications.values()
            for process in application.processes.values() if process.conflicting()]

    # RPC Command methods
    def start_application(self, strategy, application_name, wait=True):
        """ Start the application named application_name iaw the strategy and the rules file.

        *@param* ``DeploymentStrategies strategy``: the strategy used to choose addresses.

        *@param* ``str application_name``: the name of the application.

        *@param* ``bool wait``: wait for the application to be fully started.

        *@throws* ``RPCError``:

            * with code ``Faults.BAD_SUPVISORS_STATE`` if **Supvisors** is not in state ``OPERATION``,
            * with code ``Faults.BAD_STRATEGY`` if strategy is unknown to **Supvisors**,
            * with code ``Faults.BAD_NAME`` if application_name is unknown to **Supvisors**,
            * with code ``Faults.ALREADY_STARTED`` if application is ``RUNNING``,
            * with code ``Faults.ABNORMAL_TERMINATION`` if application could not be started.

        *@return* ``bool``: always ``True`` unless error or nothing to start.
        """
        self._check_operating()
        # check strategy
        if strategy not in DeploymentStrategies._values():
            raise RPCError(Faults.BAD_STRATEGY, '{}'.format(strategy))
        # check application is known
        if application_name not in self.context.applications.keys():
            raise RPCError(Faults.BAD_NAME, application_name)
        # check application is not already RUNNING
        application = self.context.applications[application_name]
        if application.state == ApplicationStates.RUNNING:
            raise RPCError(Faults.ALREADY_STARTED, application_name)
        # TODO: develop a predictive model to check if deployment can be achieved
        # if impossible due to a lack of resources, second try without optionals
        # return false if still impossible
        done = self.starter.start_application(strategy, application)
        self.logger.debug('start_application {} done={}'.format(application_name, done))
        # wait until application fully RUNNING or (failed)
        if wait and not done:
            def onwait():
                # check starter
                if self.starter.in_progress():
                    return NOT_DONE_YET
                if application.state != ApplicationStates.RUNNING:
                    raise RPCError(Faults.ABNORMAL_TERMINATION, application_name)
                return True
            onwait.delay = 0.5
            return onwait # deferred
        # if done is True, nothing to do (no deployment or impossible to deploy)
        return not done

    def stop_application(self, application_name, wait=True):
        """ Stop the application named application_name.

        *@param* ``str application_name``: the name of the application.

        *@param* ``bool wait``: wait for the application to be fully stopped.

        *@throws* ``RPCError``:

            * with code ``Faults.BAD_SUPVISORS_STATE`` if **Supvisors** is not in state ``OPERATION`` or ``CONCILIATION``,
            * with code ``Faults.BAD_NAME`` if application_name is unknown to **Supvisors**.

        *@return* ``bool``: always ``True`` unless error.
        """
        self._check_operating_conciliation()
        # check application is known
        if application_name not in self.context.applications.keys():
            raise RPCError(Faults.BAD_NAME, application_name)
        # do NOT check application state as there may be processes RUNNING although the application is declared STOPPED
        application = self.context.applications[application_name]
        done = self.stopper.stop_application(application)
        self.logger.debug('stop_application {} done={}'.format(application_name, done))
        # wait until application fully STOPPED
        if wait and not done:
            def onwait():
                # check stopper
                if self.stopper.in_progress():
                    return NOT_DONE_YET
                if application.state != ApplicationStates.STOPPED:
                    raise RPCError(Faults.ABNORMAL_TERMINATION, application_name)
                return True
            onwait.delay = 0.5
            return onwait # deferred
        # if done is True, nothing to do
        return not done

    def restart_application(self, strategy, application_name, wait=True):
        """ Restart the application named application_name iaw the strategy and the rules file.

        *@param* ``DeploymentStrategies strategy``: the strategy used to choose addresses.

        *@param* ``str application_name``: the name of the application.

        *@param* ``bool wait``: wait for the application to be fully restarted.

        *@throws* ``RPCError``:

            * with code ``Faults.BAD_SUPVISORS_STATE`` if **Supvisors** is not in state ``OPERATION``,
            * with code ``Faults.BAD_STRATEGY`` if strategy is unknown to **Supvisors**,
            * with code ``Faults.BAD_NAME`` if application_name is unknown to **Supvisors**,
            * with code ``Faults.ABNORMAL_TERMINATION`` if application could not be started.

        *@return* ``bool``: always ``True`` unless error.
        """
        self._check_operating()
        def onwait():
            # first wait for application to be stopped
            if onwait.waitstop:
                # job may be a boolean value if stop_application has nothing to do
                value = type(onwait.job) is bool or onwait.job()
                if value is True:
                    # done. request start application
                    onwait.waitstop = False
                    value = self.start_application(strategy, application_name, wait)
                    if type(value) is bool:
                        return value
                    # deferred job to wait for application to be started
                    onwait.job = value
                return NOT_DONE_YET
            return onwait.job()
        onwait.delay = 0.5
        onwait.waitstop = True
        # request stop application. job is for deferred result
        onwait.job = self.stop_application(application_name, True)
        return onwait # deferred

    def start_args(self, namespec, extra_args='', wait=True):
        """ Start a local process.
        The behaviour is different from ``supervisor.startProcess`` as it sets the process state to ``FATAL``
        instead of throwing an exception to the RPC client.
        This RPC makes it also possible to pass extra arguments to the program command line.

        *@param* ``str namespec``: the process namespec.

        *@param* ``str extra_args``: extra arguments to be passed to the command line of the program.

        *@param* ``bool wait``: wait for the process to be fully started.

        *@throws* ``RPCError``:

            * with code ``Faults.BAD_NAME`` if namespec is unknown to the local Supervisor,
            * with code ``Faults.BAD_EXTRA_ARGUMENTS`` if program is required or has a start sequence,
            * with code ``Faults.ALREADY_STARTED`` if process is ``RUNNING``,
            * with code ``Faults.ABNORMAL_TERMINATION`` if process could not be started.

        *@return* ``bool``: always ``True`` unless error.
        """
        # WARN: do NOT check OPERATION (it is used internally in DEPLOYMENT)
        application, process = self._get_application_process(namespec)
        if extra_args and not process.accept_extra_arguments():
            raise RPCError(Faults.BAD_EXTRA_ARGUMENTS, 'rules for namespec {} are not compatible with extra arguments in command line'.format(namespec))
        # update command line in process config with extra_args
        try:
            self.info_source.update_extra_args(namespec, extra_args)
        except KeyError:
            # process is unknown to the local Supervisor
            # this should not happen as Supvisors checks the configuration before it sends this request
            self.logger.error('could not find {} in supervisord processes'.format(namespec))
            raise RPCError(Faults.BAD_NAME, 'namespec {} unknown in this Supervisor instance'.format(namespec))
        # start process with Supervisor internal RPC
        try:
            cb = self.info_source.supervisor_rpc_interface.startProcess(namespec, wait)
        except RPCError, why:
            self.logger.error('start_process {} failed: {}'.format(namespec, why))
            if why.code in [Faults.NO_FILE, Faults.NOT_EXECUTABLE]:
                self.logger.warn('force supervisord internal state of {} to FATAL'.format(namespec))
                # at this stage, process is known to the local Supervisor
                self.info_source.force_process_fatal(namespec, why.text)
            # else process is already started
            # this should not happen as Supvisors checks the process state before it sends this request
            # anyway raise exception again
            raise
        return cb

    def start_process(self, strategy, namespec, extra_args='', wait=True):
        """ Start a process named namespec iaw the strategy and some of the rules file.
        WARN: the 'wait_exit' rule is not considered here.

        *@param* ``DeploymentStrategies strategy``: the strategy used to choose addresses.

        *@param* ``str namespec``: the process namespec (``name``, ``group:name``, or ``group:*``).

        *@param* ``str extra_args``: extra arguments to be passed to command line.

        *@param* ``bool wait``: wait for the process to be fully started.

        *@throws* ``RPCError``:

            * with code ``Faults.BAD_SUPVISORS_STATE`` if **Supvisors** is not in state ``OPERATION``,
            * with code ``Faults.BAD_STRATEGY`` if strategy is unknown to **Supvisors**,
            * with code ``Faults.BAD_NAME`` if namespec is unknown to **Supvisors**,
            * with code ``Faults.ALREADY_STARTED`` if process is ``RUNNING``,
            * with code ``Faults.ABNORMAL_TERMINATION`` if process could not be started.

        *@return* ``bool``: always ``True`` unless error.
        """
        self._check_operating()
        # check strategy
        if strategy not in DeploymentStrategies._values():
            raise RPCError(Faults.BAD_STRATEGY, '{}'.format(strategy))
        # check names
        application, process = self._get_application_process(namespec)
        processes = [process] if process else application.processes.values()
        # check processes are not already RUNNING
        for process in processes:
            if process.running():
                raise RPCError(Faults.ALREADY_STARTED, process.namespec())
        # start all processes
        done = True
        for process in processes:
            done &= self.starter.start_process(strategy, process, extra_args)
        self.logger.debug('startProcess {} done={}'.format(process.namespec(), done))
        # wait until application fully RUNNING or (failed)
        if wait and not done:
            def onwait():
                # check starter
                if self.starter.in_progress():
                    return NOT_DONE_YET
                for process in processes:
                    if process.stopped():
                        raise RPCError(Faults.ABNORMAL_TERMINATION, process.namespec())
                return True
            onwait.delay = 0.1
            return onwait # deferred
        # if done is True, nothing to do (no deployment or impossible to deploy)
        return not done

    def stop_process(self, namespec, wait=True):
        """ Stop the process named namespec where it is running.

        *@param* ``str namespec``: the process namespec (``name``, ``group:name``, or ``group:*``).

        *@param* ``bool wait``: wait for process to be fully stopped.

        *@throws* ``RPCError``:

            * with code ``Faults.BAD_SUPVISORS_STATE`` if **Supvisors** is not in state ``OPERATION`` or ``CONCILIATION``,
            * with code ``Faults.BAD_NAME`` if namespec is unknown to **Supvisors**.

        *@return* ``bool``: always ``True`` unless error.
        """
        self._check_operating_conciliation()
        # check names
        application, process = self._get_application_process(namespec)
        processes = [process] if process else application.processes.values()
        # stop all processes
        done = True
        for process in processes:
            self.logger.info('stopping process {}'.format(process.namespec()))
            done &= self.stopper.stop_process(process)
        # wait until processes are in STOPPED_STATES
        if wait and not done:
            def onwait():
                # check stopper
                if self.stopper.in_progress():
                    return NOT_DONE_YET
                for process in processes:
                    if process.running():
                        raise RPCError(Faults.ABNORMAL_TERMINATION, process.namespec())
                return True
            onwait.delay = 0.1
            return onwait # deferred
        return True

    def restart_process(self, strategy, namespec, extra_args='', wait=True):
        """ Restart a process named namespec iaw the strategy and some of the rules defined in the deployment file.
        WARN: the 'wait_exit' rule is not considered here.

        *@param* ``DeploymentStrategies strategy``: the strategy used to choose addresses.

        *@param* ``str namespec``: the process namespec (``name``, ``group:name``, or ``group:*``).

        *@param* ``str extra_args``: extra arguments to be passed to command line.

        *@param* ``bool wait``: wait for process to be fully stopped.

        *@throws* ``RPCError``:

            * with code ``Faults.BAD_SUPVISORS_STATE`` if **Supvisors** is not in state ``OPERATION``,
            * with code ``Faults.BAD_STRATEGY`` if strategy is unknown to **Supvisors**,
            * with code ``Faults.BAD_NAME`` if namespec is unknown to **Supvisors**,
            * with code ``Faults.ABNORMAL_TERMINATION`` if process could not be started.

        *@return* ``bool``: always ``True`` unless error.
        """
        self._check_operating()
        def onwait():
           # first wait for process to be stopped
            if callable(onwait.job):
                value = onwait.job()
                if value is NOT_DONE_YET:
                    return NOT_DONE_YET
                if onwait.stopdone:
                    # the start is completed
                    return value
            if not onwait.stopdone:
                # stop is done, whatever the result is True or False.
                onwait.stopdone = True
                # request start process
                onwait.job = self.start_process(strategy, namespec, extra_args, wait)
                return NOT_DONE_YET
            return onwait.job
        # request stop process. job is for deferred result
        onwait.delay = 0.1
        onwait.job = self.stop_process(namespec, True)
        onwait.stopdone = False
        return onwait # deferred

    def restart(self):
        """ Stops all applications and restart **Supvisors** through all Supervisor daemons.

        *@throws* ``RPCError``: with code ``Faults.BAD_SUPVISORS_STATE`` if **Supvisors** is still in state ``INITIALIZATION``.

        *@return* ``bool``: always ``True`` unless error.
        """
        self._check_from_deployment()
        self.fsm.on_restart()
        return True

    def shutdown(self):
        """ Stops all applications and shut down **Supvisors** through all Supervisor daemons.

        *@throws* ``RPCError``: with code ``Faults.BAD_SUPVISORS_STATE`` if **Supvisors** is still in state ``INITIALIZATION``.

        *@return* ``bool``: always ``True`` unless error.
        """
        self._check_from_deployment()
        self.fsm.on_shutdown()
        return True


    # utilities
    def _check_from_deployment(self):
        """ Raises a BAD_SUPVISORS_STATE exception if Supvisors' state is in INITIALIZATION. """
        self._check_state([SupvisorsStates.DEPLOYMENT, SupvisorsStates.OPERATION, SupvisorsStates.CONCILIATION,
            SupvisorsStates.RESTARTING, SupvisorsStates.SHUTTING_DOWN])

    def _check_operating_conciliation(self):
        """ Raises a BAD_SUPVISORS_STATE exception if Supvisors' state is NOT in OPERATION or CONCILIATION. """
        self._check_state([SupvisorsStates.OPERATION, SupvisorsStates.CONCILIATION])

    def _check_operating(self):
        """ Raises a BAD_SUPVISORS_STATE exception if Supvisors' state is NOT in OPERATION. """
        self._check_state([SupvisorsStates.OPERATION])

    def _check_state(self, states):
        """ Raises a BAD_SUPVISORS_STATE exception if Supvisors' state is NOT in one of the states. """
        if self.supvisors.fsm.state not in states:
            raise RPCError(Faults.BAD_SUPVISORS_STATE, 'Supvisors (state={}) not in state {} to perform request'.
                format(SupvisorsStates._to_string(self.supvisors.fsm.state), [SupvisorsStates._to_string(state) for state in states]))

    def _get_application_process(self, namespec):
        """ Return the ApplicationStatus and ProcessStatus corresponding to the namespec.
        A BAD_NAME exception is raised if the application or the process is not found. """
        application_name, process_name = split_namespec(namespec)
        return self._get_application(application_name), self._get_process(namespec) if process_name else None

    def _get_application(self, application_name):
        """ Return the ApplicationStatus corresponding to the application name.
        A BAD_NAME exception is raised if the application is not found. """
        try:
            application = self.context.applications[application_name]
        except KeyError:
            raise RPCError(Faults.BAD_NAME, 'application {} unknown in Supvisors'.format(application_name))
        return application

    def _get_process(self, namespec):
        """ Return the ProcessStatus corresponding to the namespec.
        A BAD_NAME exception is raised if the process is not found. """
        try:
            process = self.context.processes[namespec]
        except KeyError:
            raise RPCError(Faults.BAD_NAME, 'process {} unknown in Supvisors'.format(namespec))
        return process

    def _get_internal_process_rules(self, process):
        """ Return a dictionary with the rules of the process. """
        result = process.rules.serial()
        result.update({'application_name': process.application_name, 'process_name': process.process_name})
        return result
