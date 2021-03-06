#!/usr/bin/python
#-*- coding: utf-8 -*-

# ======================================================================
# Copyright 2017 Julien LE CLEACH
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

import sys
import unittest

from supvisors.tests.base import DummySupvisors


class CommanderTest(unittest.TestCase):
    """ Test case for the Commander class of the commander module. """

    def setUp(self):
        """ Create a logger that stores log traces. """
        self.supvisors = DummySupvisors()

    def test_TODO(self):
        """ Test the values set at construction. """
        from supvisors.commander import Commander
        commander = Commander(self.supvisors)
        self.assertIsNotNone(commander)


class StarterTest(unittest.TestCase):
    """ Test case for the Starter class of the commander module. """

    def setUp(self):
        """ Create a logger that stores log traces. """
        self.supvisors = DummySupvisors()

    def test_TODO(self):
        """ Test the values set at construction. """
        from supvisors.commander import Starter
        starter = Starter(self.supvisors)
        self.assertIsNotNone(starter)


class StopperTest(unittest.TestCase):
    """ Test case for the Stopper class of the commander module. """

    def setUp(self):
        """ Create a logger that stores log traces. """
        self.supvisors = DummySupvisors()

    def test_TODO(self):
        """ Test the values set at construction. """
        from supvisors.commander import Stopper
        stopper = Stopper(self.supvisors)
        self.assertIsNotNone(stopper)


def test_suite():
    return unittest.findTestCases(sys.modules[__name__])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
