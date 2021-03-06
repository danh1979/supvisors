.. _xml_rpc:

XML-RPC API
===========

The **Supvisors** XML-RPC API is an extension of the Supervisor XML-RPC API.
Detailed information can be found in the
`Supervisor XML-RPC API Documentation <http://supervisord.org/api.html#xml-rpc-api-documentation>`_.

The ``supvisors`` namespace has been added to the :command:`supervisord` XML-RPC interface.

The XML-RPC ``system.listMethods`` now provides the list of methods supported for both Supervisor and **Supvisors**.
An example is provided below.

.. code-block:: python

    server.supvisors.getState()

.. note::

    In the following, the namespec refers to the full name of the process, including the application name.
    For example: ``X11:xclock``, where ``X11`` is the name of a Supervisor group and ``xclock`` is the name
    of a Supervisor program that is referenced in the group.
    In some cases, it can also refer to all the programs of the group. For example: ``X11:*``.


.. automodule:: supvisors.rpcinterface

.. _xml_rpc_status:

Status
------

  .. autoclass:: RPCInterface

       .. automethod:: get_api_version()

       .. automethod:: get_supvisors_state()

            ================== ========= ===========
            Key                Type      Description
            ================== ========= ===========
            'statecode'        ``int``   The state of **Supvisors**, in [0;6].
            'statename'        ``str``   The string state of **Supvisors**, in [``'INITIALIZATION'``, ``'DEPLOYMENT'``, ``'OPERATION'``, ``'CONCILIATION'``, ``'RESTARTING'``, ``'SHUTTING_DOWN'``, ``'SHUTDOWN'``].
            ================== ========= ===========

       .. automethod:: get_master_address()

       .. automethod:: get_address_info(address_name)

            ================== ========= ===========
            Key                Type      Description
            ================== ========= ===========
            'address_name'     ``str``   The address of the **Supvisors** instance.
            'statecode'	       ``int``   The state of the **Supvisors** instance, in [0;5].
            'statename'	       ``str``   The string state of the **Supvisors** instance, in [``'UNKNOWN'``, ``'CHECKING'``, ``'RUNNING'``, ``'SILENT'``, ``'ISOLATING'``, ``'ISOLATED'``].
            'remote_time'      ``int``   The date, in ms, of the last heartbeat received from the **Supvisors** instance, in the remote reference time.
            'local_time'       ``int``   The date, in ms, of the last heartbeat received from the **Supvisors** instance, in the local reference time.
            'loading'          ``int``   The sum of the expected loading of the processes running on the address, in [0;100]%.
            ================== ========= ===========

       .. automethod:: get_all_addresses_info()

       .. automethod:: get_application_info(application_name)

            ================== ========= ===========
            Key                Type      Description
            ================== ========= ===========
            'application_name' ``str``   The name of the application.
            'statecode'        ``int``   The state of the application, in [0;4].
            'statename'        ``str``   The string state of the application, in [``'UNKNOWN'``, ``'STOPPED'``, ``'STARTING'``, ``'STOPPING'``, ``'RUNNING'``].
            'major_failure'    ``bool``  ``True`` if at least one required process is not started.
            'minor_failure'    ``bool``  ``True`` if at least one optional process could not be started.
            ================== ========= ===========

        .. automethod:: get_all_applications_info()

        .. automethod:: get_process_info(namespec)

            ================== ============= ===========
            Key                Type          Description
            ================== ============= ===========
            'application_name' ``str``       The name of the process' application.
            'process_name'     ``str``       The name of the process.
            'statecode'        ``int``       The state of the process, in {0, 10, 20, 30, 40, 100, 200, 1000}.
            'statename'        ``str``       The string state of the process, in [``'STOPPED'``, ``'STARTING'``, ``'RUNNING'``, ``'BACKOFF'``, ``'STOPPING'``, ``'EXITED'``, ``'FATAL'``, ``'UNKNOWN'``].
            'addresses'        ``list(str)`` The list of all addresses where the process is running.
            ================== ============= ===========

            .. note::

                If there is more than one element in the 'addresses' list, a conflict is in progress.
            

        .. automethod:: get_all_process_info()

        .. automethod:: get_process_rules(namespec)

            ================== ============= ===========
            Key                Type          Description
            ================== ============= ===========
            'application_name' ``str``       The name of the process' application.
            'process_name'     ``str``       The name of the process.
            'addresses'        ``list(str)`` The list of all addresses where the process can be started.
            'start_sequence'   ``int``       The starting rank of the process when starting the related application, in [0;127].
            'stop_sequence'    ``int``       The stopping rank of the process when stopping the related application, in [0;127].
            'required'         ``bool``      The importance of the process in the application.
            'wait_exit'        ``bool``      ``True`` if **Supvisors** has to wait for the process to exit before triggering the next deployment phase.
            'loading'          ``int``       The expected loading of the process when ``RUNNING``, in [0;100]%.
            ================== ============= ===========

        .. automethod:: get_conflicts()

            The returned structure has the same format as ``get_process_info(namespec)``.


.. _xml_rpc_supvisors:

**Supvisors** Control
---------------------

  .. autoclass:: RPCInterface

        .. automethod:: restart()

        .. automethod:: shutdown()


.. _xml_rpc_application:

Application Control
-------------------

  .. autoclass:: RPCInterface

        .. automethod:: start_application(strategy, application_name, wait=True)

        .. automethod:: stop_application(application_name, wait=True)

        .. automethod:: restart_application(strategy, application_name, wait=True)


.. _xml_rpc_process:

Process Control
---------------

  .. autoclass:: RPCInterface

        .. automethod:: start_args(namespec, extra_args=None, wait=True)

        .. automethod:: start_process(strategy, namespec, extra_args=None, wait=True)

        .. automethod:: stop_process(namespec, wait=True)

        .. automethod:: restart_process(strategy, namespec, wait=True)


XML-RPC Clients
---------------

This section explains how to use the XML-RPC API from a Python, JAVA or C++ client.


Python Client
~~~~~~~~~~~~~

There are two possibilities to perform an XML-RPC from a python client.
Both methods don't require any additional third party.
However, it is assumed that the environment parameter contains the relevant HTTP configuration,
as it would be set for a process spawed by Supervisor.
More particularly, it is expected that the following variables are set:

    * ``SUPERVISOR_SERVER_URL``: the url of the Supervisor HTTP server (ex: ``http://localhost:60000``),
    * ``SUPERVISOR_USERNAME``: the user name for the HTTP authentication (may be empty),
    * ``SUPERVISOR_PASSWORD``: the password for the HTTP authentication (may be empty).

The first is to use the ``getRPCInterface`` of the ``supervisor.childutils`` module.
This is available in Supervisor but it works only for the local address.

.. code-block:: python

    import os
    from supervisor.childutils import getRPCInterface

    proxy = getRPCInterface(os.environ)
    proxy.supervisor.getState()
    proxy.supvisors.get_supvisors_state()

The second possibility is to use the ``getRPCInterface`` of the ``supvisors.rpcrequests`` module.
This is available in **Supvisors** and works for all addresses with a Supervisor daemon running with the same HTTP configuration as the local one.

.. code-block:: python

    import os
    from supvisors.rpcrequests import getRPCInterface

    proxy = getRPCInterface(address, os.environ)
    proxy.supervisor.getState()
    proxy.supvisors.get_supvisors_state()


JAVA Client
~~~~~~~~~~~

There is JAVA client *supervisord4j* referenced in the
`Supervisor documentation <http://supervisord.org/plugins.html#libraries-that-integrate-third-party-applications-with-supervisor>`_.
However, it comes with the following drawbacks, taken from the ``README.md`` of
`supervisord4j <https://github.com/satifanie/supervisord4j>`_:

    * of course, it doesn't include the **Supvisors** XML-RPC API,
    * some XML-RPC are not implemented,
    * some implemented XML-RPC are not tested.

**Supvisors** provides a JAVA client in the :file:`client/java` directory of the **Supvisors** installation directory.
This classes of the ``org.supvisors.rpc`` package implement all XML-RPC of all interfaces (``system``, ``supervisor`` and ``supvisors``).

It requires the following additional dependency: `Apache XML-RPC <https://ws.apache.org/xmlrpc>`_.
The binary JAR of Apache XML-RPC 3.1.3 is available in the
`MAVEN repository <https://mvnrepository.com/artifact/org.apache.xmlrpc/xmlrpc/3.1.3>`_.

.. code-block:: java

    import org.supvisors.rpc.*;

    // create proxy
    SupervisorXmlRpcClient client = new SupervisorXmlRpcClient("10.0.0.1", 60000, "toto", "p@$$w0rd");

    // Supervisor XML-RPC
    SupervisorXmlRpc supervisor = new SupervisorXmlRpc(client);
    System.out.println(supervisor.getState());

    // Supvisors XML-RPC
    SupvisorsXmlRpc supvisors = new SupvisorsXmlRpc(client);
    System.out.println(supvisors.getSupvisorsState());


C++ Client
~~~~~~~~~~

Not implemented yet

