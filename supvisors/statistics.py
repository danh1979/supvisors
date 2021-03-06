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

from psutil import cpu_count, cpu_times, net_io_counters, virtual_memory, Process, NoSuchProcess
from time import time

from supvisors.utils import mean


# CPU statistics
def instant_cpu_statistics():
    """ Return the instant work+idle jiffies for all the processors.
    The average on all processors is inserted in front of the list. """
    work = [ ]
    idle = [ ]
    # CPU details
    cpu_stats = cpu_times(percpu=True)
    for cpu_stat in cpu_stats:
        work.append(cpu_stat.user + cpu_stat.nice + cpu_stat.system + cpu_stat.irq + cpu_stat.softirq + cpu_stat.steal + cpu_stat.guest)
        idle.append(cpu_stat.idle + cpu_stat.iowait)
    # return adding CPU average in front of lists
    work.insert(0, mean(work))
    idle.insert(0, mean(idle))
    return zip(work, idle)

def cpu_statistics(last, ref):
    """ Return the CPU loading for all the processors between last and ref measures.
    The average on all processors is inserted in front of the list. """
    cpu = []
    for unit in zip(last, ref):
        work = unit[0][0] - unit[1][0]
        idle = unit[0][1] - unit[1][1]
        total = work + idle
        cpu.append(100.0 * work / total if total else 0)
    return cpu

def cpu_total_work(last, ref):
    """ Return the total work on the average CPU between last and ref measures. """
    work = last[0][0] - ref[0][0]
    idle = last[0][1] - ref[0][1]
    return work + idle


# Memory statistics
def instant_memory_statistics():
    """ Return the instant value of the memory reserved.
    This is different from the memory used as it does not include the percent of memory that is available (in cache or swap). """
    return virtual_memory().percent


# Network statistics
def instant_io_statistics():
    """ Return the instant values of receive / sent bytes per network interface. """
    result = {}
    # IO details
    io_stats = net_io_counters(pernic=True)
    for intf, io_stat in io_stats.items():
        result[intf] = io_stat.bytes_recv, io_stat.bytes_sent
    return result

def io_statistics(last, ref, duration):
    """ Return the rate of receive / sent bytes per second per network interface. """
    io_stats = {}
    for intf, (last_recv, last_sent) in last.items():
        if intf in ref.keys():
            ref_recv, ref_sent = ref[intf]
            # Warning taken from psutil documentation (https://pythonhosted.org/psutil/#network)
            # on some systems such as Linux, on a very busy or long-lived system these numbers may wrap (restart from zero),
            # see issues #802. Applications should be prepared to deal with that.
            if ref_recv <= last_recv and ref_sent <= last_sent:
                recv_bytes = last_recv - ref_recv
                sent_bytes = last_sent - ref_sent
                # result in kilo bits per second (bytes / 1024 * 8)
                io_stats[intf] = recv_bytes / duration / 128, sent_bytes / duration / 128
    return io_stats


# Process statistics
def instant_process_statistics(pid):
    """ Return the instant jiffies and memory values for the process identified by pid. """
    work = memory = 0
    try:
        proc = Process(pid)
        for p in [proc] + proc.children(recursive=True):
            work += sum(p.cpu_times())
            memory += p.memory_percent()
    except (NoSuchProcess, ValueError):
        # process may have disappeared in the interval
        pass
    # take into account the number of processes for the process work 
    return work / cpu_count(), memory

def cpu_process_statistics(last, ref, total_work):
    """ Return the CPU loading of the process between last and ref measures. """
    # process may have been started between ref and last
    return 100.0 * (last - ref) / total_work


# Snapshot of all resources
def instant_statistics(named_pid_list):
    """ Return a tuple of all measures taken on the CPU, Memory and IO resources. """
    proc_statistics = {process_name: (pid, instant_process_statistics(pid)) for process_name, pid in named_pid_list}
    return time(), instant_cpu_statistics(), instant_memory_statistics(), instant_io_statistics(), proc_statistics


# Calculate resources taken between two snapshots
def statistics(last, ref):
    """ Return resources statistics from two series of measures. """
    # for use in client display
    duration = last[0] - ref[0]
    cpu = cpu_statistics(last[1], ref[1])
    mem = last[2]
    io = io_statistics(last[3], ref[3], duration)
    # process statistics
    work = cpu_total_work(last[1], ref[1])
    proc = {}
    # when tuples are unserialized through JSON, they become lists
    for process_name, last_pid_stats in last[4].items():
        # find same process in ref
        ref_pid_stats = ref[4].get(process_name, None)
        # calculate cpu if ref is found
        proc_cpu = 0
        # pid must be identical (in case of process restart in the interval)
        if ref_pid_stats and last_pid_stats[0] == ref_pid_stats[0]:
            # need the work jiffies in the interval
            proc_cpu = cpu_process_statistics(last_pid_stats[1][0], ref_pid_stats[1][0], work)
        proc[process_name, last_pid_stats[0]] = proc_cpu, last_pid_stats[1][1]
    return last[0], cpu, mem, io, proc


# Class for statistics storage
class StatisticsInstance(object):
    """ This class handles resources statistics for a given address and period. """

    def __init__(self, period, depth):
        # as period is a multiple of 5 and a call to pushStatistics is expected every 5 seconds, use period as a simple counter
        self.period = period / 5
        self.depth = depth
        self.clear()

    def clear(self):
        self.counter = -1
        self.ref_stats = None
        # data structures
        self.cpu = []
        self.mem = []
        self.io = {}
        self.proc = {}

    def find_process_stats(self, namespec):
        return next((stats for (process_name, pid), stats in self.proc.items() if process_name == namespec), None)

    def push_statistics(self, stats):
        self.counter += 1
        if self.counter % self.period == 0:
            if self.ref_stats:
                # rearrange data so that there is less processing afterwards
                integ_stats = statistics(stats, self.ref_stats)
                # add new CPU values to CPU lists
                for lst in self.cpu:
                	lst.append(integ_stats[1].pop(0))
                	self.trunc_depth(lst)
                # add new Mem value to MEM list
                self.mem.append(integ_stats[2])
                self.trunc_depth(self.mem)
                # add new IO values to IO list
                for intf, bytes in self.io.items():
                    new_bytes = integ_stats[3].pop(intf)
                    bytes[0].append(new_bytes[0])
                    bytes[1].append(new_bytes[1])
                    # remove too old values when max depth is reached
                    self.trunc_depth(bytes[0])
                    self.trunc_depth(bytes[1])
                # add new Process CPU / Mem values to Process list
                # as process list is dynamic, there are special rules
                destroy_list = []
                for named_pid, (cpu_stats, mem_stats) in self.proc.items():
                    new_values = integ_stats[4].pop(named_pid, None)
                    if new_values is None:
                        # element is obsolete
                        destroy_list.append(named_pid)
                    else:
                        new_cpu_value, new_mem_value = new_values
                        cpu_stats.append(new_cpu_value)
                        mem_stats.append(new_mem_value)
                        # remove too old values when max depth is reached
                        self.trunc_depth(cpu_stats)
                        self.trunc_depth(mem_stats)
                # destroy obsolete elements
                for named_pid in destroy_list:
                	del self.proc[named_pid]
                # add new elements
                for named_pid, (new_cpu_value, new_mem_value) in integ_stats[4].items():
                	self.proc[named_pid] = [new_cpu_value], [new_mem_value]
            else:
                # init data structures (mem unchanged)
                self.cpu = [[] for _ in stats[1]]
                self.io = {intf: ([], []) for intf in stats[3].keys()}
                self.proc = {(process_name, pid_stats[0]): ([], []) for process_name, pid_stats in stats[4].items()}
            self.ref_stats = stats

    # remove first data of all lists if size exceeds depth
    def trunc_depth(self, lst):
        """ Ensure that the list does not exceed the maimum historic size. """
        while len(lst) > self.depth:
            lst.pop(0)


# Class used to compile statistics coming from all addresses
class StatisticsCompiler(object):
    """ This class handles stores statistics for all addresses and periods. """

    def __init__(self, supvisors):
        """ Initializes the statistics dictionary.
        The dictionary contains a StatisticsInstance entry for each pair of address and period. """
        self.data = {address: {period: StatisticsInstance(period, supvisors.options.stats_histo)
            for period in supvisors.options.stats_periods}
            for address in supvisors.address_mapper.addresses}

    def clear(self, address):
        """  For a given address, clear the StatisticsInstance for all periods. """
        for period in self.data[address].values():
            period.clear()

    def push_statistics(self, address, stats):
        """  Insert a new statistics measure for address. """
        for period in self.data[address].values():
            period.push_statistics(stats)
