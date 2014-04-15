# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for the behaviour of unit tests.

Many tests in this module follow a simple pattern.  A mixin is defined which
includes test methods for a certain feature.  The mixin is inherited from twice,
once by a class also inheriting from SynchronousTestCase and once from a class
inheriting from TestCase.  These two subclasses are named like
I{SynchronousFooTests} and I{AsynchronousFooTests}, where I{Foo} is related to
the name of the mixin.  Sometimes the mixin is defined in another module, along
with the synchronous subclass.  The mixin is imported into this module to define
the asynchronous subclass.

This pattern allows the same tests to be applied to the two base test case
classes trial provides, ensuring their behavior is the same.

Most new tests should be added in this pattern.  Tests for functionality which
is intentionally only provided by TestCase, not SynchronousTestCase, is excepted
of course.
"""

from __future__ import division, absolute_import

import gc, sys, weakref
import unittest as pyunit

from twisted.python.compat import _PY3, NativeStringIO
from twisted.internet import defer, reactor
from twisted.trial import unittest, reporter, util
if not _PY3:
    from twisted.trial import runner
from twisted.trial.test import erroneous
from twisted.trial.test.test_suppression import SuppressionMixin


# Skip messages that are used in multiple places:
_PY3PORTNEEDED = "Requires runner and/or reporter to be ported (#5964, #5965)"


class ResultsTestMixin(object):
    """
    Provide useful APIs for test cases that are about test cases.
    """
    def loadSuite(self, suite):
        """
        Load tests from the given test case class and create a new reporter to
        use for running it.
        """
        self.loader = pyunit.TestLoader()
        self.suite = self.loader.loadTestsFromTestCase(suite)
        self.reporter = reporter.TestResult()

    def test_setUp(self):
        """
        test the setup
        """
        self.failUnless(self.reporter.wasSuccessful())
        self.assertEqual(self.reporter.errors, [])
        self.assertEqual(self.reporter.failures, [])
        self.assertEqual(self.reporter.skips, [])

    def assertCount(self, numTests):
        """
        Asserts that the test count is plausable
        """
        self.assertEqual(self.suite.countTestCases(), numTests)
        self.suite(self.reporter)
        self.assertEqual(self.reporter.testsRun, numTests)


class SuccessMixin(object):
    """
    Tests for the reporting of successful tests in L{twisted.trial.unittest.TestCase}.
    """
    def setUp(self):
        """
        Setup our test case
        """
        self.result = reporter.TestResult()

    def test_successful(self):
        """
        A successful test, used by other tests.
        """

    def assertSuccessful(self, test, result):
        """
        Utility function -- assert there is one success and the state is 
        plausable
        """
        self.assertEqual(result.successes, 1)
        self.assertEqual(result.failures, [])
        self.assertEqual(result.errors, [])
        self.assertEqual(result.expectedFailures, [])
        self.assertEqual(result.unexpectedSuccesses, [])
        self.assertEqual(result.skips, [])

    def test_successfulIsReported(self):
        """
        Test that when a successful test is run, it is reported as a success,
        and not as any other kind of result.
        """
        test = self.__class__('test_successful')
        test.run(self.result)
        self.assertSuccessful(test, self.result)

    def test_defaultIsSuccessful(self):
        """
        The test case type can be instantiated with no arguments, run, and
        reported as being successful.
        """
        test = self.__class__()
        test.run(self.result)
        self.assertSuccessful(test, self.result)

    def test_noReference(self):
        """
        Test that no reference is kept on a successful test.
        """
        test = self.__class__('test_successful')
        ref = weakref.ref(test)
        test.run(self.result)
        self.assertSuccessful(test, self.result)
        del test
        gc.collect()
        self.assertIdentical(ref(), None)


class SynchronousSuccessTests(SuccessMixin, unittest.SynchronousTestCase):
    """
    Tests for the reporting of successful tests in the synchronous case.
    """


class AsynchronousSuccessTests(SuccessMixin, unittest.TestCase):
    """
    Tests for the reporting of successful tests in the synchronous case.
    """


class SkipMethodsMixin(ResultsTestMixin):
    """
    Tests for the reporting of skipping tests in L{twisted.trial.unittest.TestCase}.
    """
    def setUp(self):
        """
        Setup our test case
        """
        self.loadSuite(self.Skipping)

    def test_counting(self):
        """
        Assert that there are three tests.
        """
        self.assertCount(3)

    def test_results(self):
        """
        Running a suite in which all methods are individually set to skip
        produces a successful result with no recorded errors or failures, all
        the skipped methods recorded as skips, and no methods recorded as
        successes.
        """
        self.suite(self.reporter)
        self.assertTrue(self.reporter.wasSuccessful())
        self.assertEqual(self.reporter.errors, [])
        self.assertEqual(self.reporter.failures, [])
        self.assertEqual(len(self.reporter.skips), 3)
        self.assertEqual(self.reporter.successes, 0)

    def test_setUp(self):
        """
        Running a suite in which all methods are skipped by C{setUp} raising
        L{SkipTest} produces a successful result with no recorded errors or
        failures, all skipped methods recorded as skips, and no methods recorded
        as successes.
        """
        self.loadSuite(self.SkippingSetUp)
        self.suite(self.reporter)
        self.assertTrue(self.reporter.wasSuccessful())
        self.assertEqual(self.reporter.errors, [])
        self.assertEqual(self.reporter.failures, [])
        self.assertEqual(len(self.reporter.skips), 2)
        self.assertEqual(self.reporter.successes, 0)

    def test_reasons(self):
        """
        Test that reasons work
        """
        self.suite(self.reporter)
        prefix = 'test_'
        # whiteboxing reporter
        for test, reason in self.reporter.skips:
            self.assertEqual(test.shortDescription()[len(prefix):],
                                 str(reason))

    def test_deprecatedSkipWithoutReason(self):
        """
        If a test method raises L{SkipTest} with no reason, a deprecation
        warning is emitted.
        """
        self.loadSuite(self.DeprecatedReasonlessSkip)
        self.suite(self.reporter)
        warnings = self.flushWarnings([
                self.DeprecatedReasonlessSkip.test_1])
        self.assertEqual(1, len(warnings))
        self.assertEqual(DeprecationWarning, warnings[0]['category'])
        self.assertEqual(
            "Do not raise unittest.SkipTest with no arguments! Give a reason "
            "for skipping tests!",
            warnings[0]['message'])


class SynchronousSkipMethodTests(SkipMethodsMixin, unittest.SynchronousTestCase):
    """
    Tests for the reporting of skipping tests in the synchronous case.

    See: L{twisted.trial.test.test_tests.SkipMethodsMixin}
    """
    from twisted.trial.test.skipping import (
        SynchronousSkipping as Skipping,
        SynchronousSkippingSetUp as SkippingSetUp,
        SynchronousDeprecatedReasonlessSkip as DeprecatedReasonlessSkip)


class AsynchronousSkipMethodTests(SkipMethodsMixin, unittest.TestCase):
    """
    Tests for the reporting of skipping tests in the asynchronous case.

    See: L{twisted.trial.test.test_tests.SkipMethodsMixin}
    """
    from twisted.trial.test.skipping import (
        AsynchronousSkipping as Skipping,
        AsynchronousSkippingSetUp as SkippingSetUp,
        AsynchronousDeprecatedReasonlessSkip as DeprecatedReasonlessSkip)


class SkipClassesMixin(ResultsTestMixin):
    """
    Test the class skipping features of L{twisted.trial.unittest.TestCase}.
    """
    def setUp(self):
        """
        Setup our test case
        """
        self.loadSuite(self.SkippedClass)
        self.SkippedClass._setUpRan = False

    def test_counting(self):
        """
        Skipped test methods still contribute to the total test count.
        """
        self.assertCount(4)

    def test_setUpRan(self):
        """
        The C{setUp} method is not called if the class is set to skip.
        """
        self.suite(self.reporter)
        self.assertFalse(self.SkippedClass._setUpRan)

    def test_results(self):
        """
        Skipped test methods don't cause C{wasSuccessful} to return C{False},
        nor do they contribute to the C{errors} or C{failures} of the reporter,
        or to the count of successes.  They do, however, add elements to the
        reporter's C{skips} list.
        """
        self.suite(self.reporter)
        self.assertTrue(self.reporter.wasSuccessful())
        self.assertEqual(self.reporter.errors, [])
        self.assertEqual(self.reporter.failures, [])
        self.assertEqual(len(self.reporter.skips), 4)
        self.assertEqual(self.reporter.successes, 0)

    def test_reasons(self):
        """
        Test methods which raise L{unittest.SkipTest} or have their C{skip}
        attribute set to something are skipped.
        """
        self.suite(self.reporter)
        expectedReasons = ['class', 'skip2', 'class', 'class']
        # whitebox reporter
        reasonsGiven = [reason for test, reason in self.reporter.skips]
        self.assertEqual(expectedReasons, reasonsGiven)


class SynchronousSkipClassTests(SkipClassesMixin, unittest.SynchronousTestCase):
    """
    Test the class skipping features in the synchronous case.

    See: L{twisted.trial.test.test_tests.SkipClassesMixin}
    """
    from twisted.trial.test.skipping import (
        SynchronousSkippedClass as SkippedClass)


class AsynchronousSkipClassTests(SkipClassesMixin, unittest.TestCase):
    """
    Test the class skipping features in the asynchronous case.

    See: L{twisted.trial.test.test_tests.SkipClassesMixin}
    """
    from twisted.trial.test.skipping import (
        AsynchronousSkippedClass as SkippedClass)


class TodoMixin(ResultsTestMixin):
    """
    Tests for the individual test method I{expected failure} features of
    L{twisted.trial.unittest.TestCase}.
    """
    def setUp(self):
        """
        Setup our test case
        """
        self.loadSuite(self.Todo)

    def test_counting(self):
        """
        Ensure that we've got three test cases.
        """
        self.assertCount(3)

    def test_results(self):
        """
        Running a suite in which all methods are individually marked as expected
        to fail produces a successful result with no recorded errors, failures,
        or skips, all methods which fail and were expected to fail recorded as
        C{expectedFailures}, and all methods which pass but which were expected
        to fail recorded as C{unexpectedSuccesses}.  Additionally, no tests are
        recorded as successes.
        """
        self.suite(self.reporter)
        self.assertTrue(self.reporter.wasSuccessful())
        self.assertEqual(self.reporter.errors, [])
        self.assertEqual(self.reporter.failures, [])
        self.assertEqual(self.reporter.skips, [])
        self.assertEqual(len(self.reporter.expectedFailures), 2)
        self.assertEqual(len(self.reporter.unexpectedSuccesses), 1)
        self.assertEqual(self.reporter.successes, 0)

    def test_expectedFailures(self):
        """
        Ensure that expected failures are handled properly.
        """
        self.suite(self.reporter)
        expectedReasons = ['todo1', 'todo2']
        reasonsGiven = [ r.reason
                         for t, e, r in self.reporter.expectedFailures ]
        self.assertEqual(expectedReasons, reasonsGiven)

    def test_unexpectedSuccesses(self):
        """
        Ensure that unexpected successes are caught.
        """
        self.suite(self.reporter)
        expectedReasons = ['todo3']
        reasonsGiven = [ r.reason
                         for t, r in self.reporter.unexpectedSuccesses ]
        self.assertEqual(expectedReasons, reasonsGiven)

    def test_expectedSetUpFailure(self):
        """
        C{setUp} is excluded from the failure expectation defined by a C{todo}
        attribute on a test method.
        """
        self.loadSuite(self.SetUpTodo)
        self.suite(self.reporter)
        self.assertFalse(self.reporter.wasSuccessful())
        self.assertEqual(len(self.reporter.errors), 1)
        self.assertEqual(self.reporter.failures, [])
        self.assertEqual(self.reporter.skips, [])
        self.assertEqual(len(self.reporter.expectedFailures), 0)
        self.assertEqual(len(self.reporter.unexpectedSuccesses), 0)
        self.assertEqual(self.reporter.successes, 0)

    def test_expectedTearDownFailure(self):
        """
        C{tearDown} is excluded from the failure expectation defined by a C{todo}
        attribute on a test method.
        """
        self.loadSuite(self.TearDownTodo)
        self.suite(self.reporter)
        self.assertFalse(self.reporter.wasSuccessful())
        self.assertEqual(len(self.reporter.errors), 1)
        self.assertEqual(self.reporter.failures, [])
        self.assertEqual(self.reporter.skips, [])
        self.assertEqual(len(self.reporter.expectedFailures), 0)
        # This seems strange, since tearDown raised an exception.  However, the
        # test method did complete without error.  The tearDown error is
        # reflected in the errors list, checked above.
        self.assertEqual(len(self.reporter.unexpectedSuccesses), 1)
        self.assertEqual(self.reporter.successes, 0)


class SynchronousTodoTests(TodoMixin, unittest.SynchronousTestCase):
    """
    Test the class skipping features in the synchronous case.

    See: L{twisted.trial.test.test_tests.TodoMixin}
    """
    from twisted.trial.test.skipping import (
        SynchronousTodo as Todo,
        SynchronousSetUpTodo as SetUpTodo,
        SynchronousTearDownTodo as TearDownTodo)


class AsynchronousTodoTests(TodoMixin, unittest.TestCase):
    """
    Test the class skipping features in the asynchronous case.

    See: L{twisted.trial.test.test_tests.TodoMixin}
    """
    from twisted.trial.test.skipping import (
        AsynchronousTodo as Todo,
        AsynchronousSetUpTodo as SetUpTodo,
        AsynchronousTearDownTodo as TearDownTodo)


class ClassTodoMixin(ResultsTestMixin):
    """
    Tests for the class-wide I{expected failure} features of
    L{twisted.trial.unittest.TestCase}.
    """
    def setUp(self):
        """
        Setup our test case
        """
        self.loadSuite(self.TodoClass)

    def test_counting(self):
        """
        Ensure that we've got four test cases.
        """
        self.assertCount(4)

    def test_results(self):
        """
        Running a suite in which an entire class is marked as expected to fail
        produces a successful result with no recorded errors, failures, or
        skips, all methods which fail and were expected to fail recorded as
        C{expectedFailures}, and all methods which pass but which were expected
        to fail recorded as C{unexpectedSuccesses}.  Additionally, no tests are
        recorded as successes.
        """
        self.suite(self.reporter)
        self.assertTrue(self.reporter.wasSuccessful())
        self.assertEqual(self.reporter.errors, [])
        self.assertEqual(self.reporter.failures, [])
        self.assertEqual(self.reporter.skips, [])
        self.assertEqual(len(self.reporter.expectedFailures), 2)
        self.assertEqual(len(self.reporter.unexpectedSuccesses), 2)
        self.assertEqual(self.reporter.successes, 0)

    def test_expectedFailures(self):
        """
        Ensure that expected failures are handled properly.
        """
        self.suite(self.reporter)
        expectedReasons = ['method', 'class']
        reasonsGiven = [ r.reason
                         for t, e, r in self.reporter.expectedFailures ]
        self.assertEqual(expectedReasons, reasonsGiven)

    def test_unexpectedSuccesses(self):
        """
        Ensure that unexpected successes are caught.
        """
        self.suite(self.reporter)
        expectedReasons = ['method', 'class']
        reasonsGiven = [ r.reason
                         for t, r in self.reporter.unexpectedSuccesses ]
        self.assertEqual(expectedReasons, reasonsGiven)


class SynchronousClassTodoTests(ClassTodoMixin, unittest.SynchronousTestCase):
    """
    Tests for the class-wide I{expected failure} features in the synchronous case.

    See: L{twisted.trial.test.test_tests.ClassTodoMixin}
    """
    from twisted.trial.test.skipping import (
        SynchronousTodoClass as TodoClass)


class AsynchronousClassTodoTests(ClassTodoMixin, unittest.TestCase):
    """
    Tests for the class-wide I{expected failure} features in the asynchronous case.

    See: L{twisted.trial.test.test_tests.ClassTodoMixin}
    """
    from twisted.trial.test.skipping import (
        AsynchronousTodoClass as TodoClass)


class StrictTodoMixin(ResultsTestMixin):
    """
    Tests for the I{expected failure} features of
    L{twisted.trial.unittest.TestCase} in which the exact failure which is
    expected is indicated.
    """
    def setUp(self):
        """
        Setup our test case
        """
        self.loadSuite(self.StrictTodo)

    def test_counting(self):
        """
        Assert there are seven test cases
        """
        self.assertCount(7)

    def test_results(self):
        """
        A test method which is marked as expected to fail with a particular
        exception is only counted as an expected failure if it does fail with
        that exception, not if it fails with some other exception.
        """
        self.suite(self.reporter)
        self.assertFalse(self.reporter.wasSuccessful())
        self.assertEqual(len(self.reporter.errors), 2)
        self.assertEqual(len(self.reporter.failures), 1)
        self.assertEqual(len(self.reporter.expectedFailures), 3)
        self.assertEqual(len(self.reporter.unexpectedSuccesses), 1)
        self.assertEqual(self.reporter.successes, 0)
        self.assertEqual(self.reporter.skips, [])

    def test_expectedFailures(self):
        """
        Ensure that expected failures are handled properly.
        """
        self.suite(self.reporter)
        expectedReasons = ['todo1', 'todo2', 'todo5']
        reasonsGotten = [ r.reason
                          for t, e, r in self.reporter.expectedFailures ]
        self.assertEqual(expectedReasons, reasonsGotten)

    def test_unexpectedSuccesses(self):
        """
        Ensure that unexpected successes are caught.
        """
        self.suite(self.reporter)
        expectedReasons = [([RuntimeError], 'todo7')]
        reasonsGotten = [ (r.errors, r.reason)
                          for t, r in self.reporter.unexpectedSuccesses ]
        self.assertEqual(expectedReasons, reasonsGotten)


class SynchronousStrictTodoTests(StrictTodoMixin, unittest.SynchronousTestCase):
    """
    Tests for the expected failure case when the exact failure that is expected
    is indicated in the synchronous case

    See: L{twisted.trial.test.test_tests.StrictTodoMixin}
    """
    from twisted.trial.test.skipping import (
        SynchronousStrictTodo as StrictTodo)



class AsynchronousStrictTodoTests(StrictTodoMixin, unittest.TestCase):
    """
    Tests for the expected failure case when the exact failure that is expected
    is indicated in the asynchronous case

    See: L{twisted.trial.test.test_tests.StrictTodoMixin}
    """
    from twisted.trial.test.skipping import (
        AsynchronousStrictTodo as StrictTodo)



class TestReactorCleanup(unittest.SynchronousTestCase):
    """
    Tests for cleanup and reporting of reactor event sources left behind by test
    methods.
    """
    if _PY3:
        skip = _PY3PORTNEEDED

    def setUp(self):
        """
        Setup our test case
        """
        self.result = reporter.Reporter(NativeStringIO())
        self.loader = runner.TestLoader()

    def test_leftoverSockets(self):
        """
        Trial reports a L{util.DirtyReactorAggregateError} if a test leaves
        sockets behind.
        """
        suite = self.loader.loadMethod(
            erroneous.SocketOpenTest.test_socketsLeftOpen)
        suite.run(self.result)
        self.failIf(self.result.wasSuccessful())
        # socket cleanup happens at end of class's tests.
        # all the tests in the class are successful, even if the suite
        # fails
        self.assertEqual(self.result.successes, 1)
        failure = self.result.errors[0][1]
        self.failUnless(failure.check(util.DirtyReactorAggregateError))

    def test_leftoverPendingCalls(self):
        """
        Trial reports a L{util.DirtyReactorAggregateError} and fails the test
        if a test leaves a L{DelayedCall} hanging.
        """
        suite = erroneous.ReactorCleanupTests('test_leftoverPendingCalls')
        suite.run(self.result)
        self.failIf(self.result.wasSuccessful())
        failure = self.result.errors[0][1]
        self.assertEqual(self.result.successes, 0)
        self.failUnless(failure.check(util.DirtyReactorAggregateError))


class FixtureMixin(object):
    """
    Tests for broken fixture helper methods (e.g. setUp, tearDown).
    """
    def setUp(self):
        """
        Setup our test case
        """
        self.reporter = reporter.Reporter()
        self.loader = pyunit.TestLoader()

    def test_brokenSetUp(self):
        """
        When setUp fails, the error is recorded in the result object.
        """
        suite = self.loader.loadTestsFromTestCase(self.TestFailureInSetUp)
        suite.run(self.reporter)
        self.assertTrue(len(self.reporter.errors) > 0)
        self.assertIsInstance(
            self.reporter.errors[0][1].value, erroneous.FoolishError)
        self.assertEqual(0, self.reporter.successes)

    def test_brokenTearDown(self):
        """
        When tearDown fails, the error is recorded in the result object.
        """
        suite = self.loader.loadTestsFromTestCase(self.TestFailureInTearDown)
        suite.run(self.reporter)
        errors = self.reporter.errors
        self.assertTrue(len(errors) > 0)
        self.assertIsInstance(errors[0][1].value, erroneous.FoolishError)
        self.assertEqual(0, self.reporter.successes)


class SynchronousFixtureTest(FixtureMixin, unittest.SynchronousTestCase):
    """
    Tests for broken fixture helper methods in the synchronous case

    See: L{twisted.trial.test.test_tests.FixtureMixin}
    """
    from twisted.trial.test.erroneous import (
        SynchronousTestFailureInSetUp as TestFailureInSetUp,
        SynchronousTestFailureInTearDown as TestFailureInTearDown)


class AsynchronousFixtureTest(FixtureMixin, unittest.TestCase):
    """
    Tests for broken fixture helper methods in the asynchronous case

    See: L{twisted.trial.test.test_tests.FixtureMixin}
    """
    from twisted.trial.test.erroneous import (
        AsynchronousTestFailureInSetUp as TestFailureInSetUp,
        AsynchronousTestFailureInTearDown as TestFailureInTearDown)


class AsynchronousSuppressionTest(SuppressionMixin, unittest.TestCase):
    """
    Tests for the warning suppression features of 
    L{twisted.trial.unittest.TestCase}

    See L{twisted.trial.test.test_suppression.SuppressionMixin}
    """
    from twisted.trial.test.suppression import (
        AsynchronousTestSetUpSuppression as TestSetUpSuppression,
        AsynchronousTestTearDownSuppression as TestTearDownSuppression,
        AsynchronousTestSuppression as TestSuppression,
        AsynchronousTestSuppression2 as TestSuppression2)


class GCMixin:
    """
    I provide a few mock tests that log setUp, tearDown, test execution and
    garbage collection. I'm used to test whether gc.collect gets called.
    """

    if _PY3:
        skip = _PY3PORTNEEDED

    class BasicTest(unittest.SynchronousTestCase):
        """
        Mock test to run.
        """
        def setUp(self):
            """
            Mock setUp
            """
            self._log('setUp')
        def test_foo(self):
            """
            Mock test case
            """
            self._log('test')
        def tearDown(self):
            """
            Mock tear tearDown
            """
            self._log('tearDown')


    def _log(self, msg):
        """
        Log function
        """
        self._collectCalled.append(msg)

    def collect(self):
        """Fake gc.collect"""
        self._log('collect')

    def setUp(self):
        """
        Setup our test case
        """
        self._collectCalled = []
        self.BasicTest._log = self._log
        self._oldCollect = gc.collect
        gc.collect = self.collect

    def tearDown(self):
        """
        Tear down the test
        """
        gc.collect = self._oldCollect


class TestGarbageCollectionDefault(GCMixin, unittest.SynchronousTestCase):
    """
    By default, tests should not force garbage collection.
    """

    def test_collectNotDefault(self):
        """
        By default, tests should not force garbage collection.
        """
        test = self.BasicTest('test_foo')
        result = reporter.TestResult()
        test.run(result)
        self.assertEqual(self._collectCalled, ['setUp', 'test', 'tearDown'])



class TestGarbageCollection(GCMixin, unittest.SynchronousTestCase):
    """
    Test that, when force GC, it works.
    """
    def test_collectCalled(self):
        """
        test gc.collect is called before and after each test.
        """
        test = TestGarbageCollection.BasicTest('test_foo')
        test = unittest._ForceGarbageCollectionDecorator(test)
        result = reporter.TestResult()
        test.run(result)
        self.assertEqual(
            self._collectCalled,
            ['collect', 'setUp', 'test', 'tearDown', 'collect'])


class TestUnhandledDeferred(unittest.SynchronousTestCase):
    """
    Test what happens when we have an unhandled deferred left around after
    a test.
    """

    if _PY3:
        skip = _PY3PORTNEEDED

    def setUp(self):
        """
        Setup our test case
        """
        from twisted.trial.test import weird
        # test_unhandledDeferred creates a cycle. we need explicit control of gc
        gc.disable()
        self.test1 = unittest._ForceGarbageCollectionDecorator(
            weird.TestBleeding('test_unhandledDeferred'))

    def test_isReported(self):
        """
        Forcing garbage collection should cause unhandled Deferreds to be
        reported as errors.
        """
        result = reporter.TestResult()
        self.test1(result)
        self.assertEqual(len(result.errors), 1,
                         'Unhandled deferred passed without notice')

    def test_doesntBleed(self):
        """
        Forcing garbage collection in the test should mean that there are
        no unreachable cycles immediately after the test completes.
        """
        result = reporter.TestResult()
        self.test1(result)
        self.flushLoggedErrors() # test1 logs errors that get caught be us.
        # test1 created unreachable cycle.
        # it & all others should have been collected by now.
        n = gc.collect()
        self.assertEqual(n, 0, 'unreachable cycle still existed')
        # check that last gc.collect didn't log more errors
        x = self.flushLoggedErrors()
        self.assertEqual(len(x), 0, 'Errors logged after gc.collect')

    def tearDown(self):
        """
        Tear down the test
        """
        gc.collect()
        gc.enable()
        self.flushLoggedErrors()


class AddCleanupMixin(object):
    """
    Test the addCleanup method of TestCase.
    """
    def setUp(self):
        """
        Setup our test case
        """
        super(AddCleanupMixin, self).setUp()
        self.result = reporter.TestResult()
        self.test = self.AddCleanup()

    def test_addCleanupCalledIfSetUpFails(self):
        """
        Callables added with C{addCleanup} are run even if setUp fails.
        """
        self.test.setUp = self.test.brokenSetUp
        self.test.addCleanup(self.test.append, 'foo')
        self.test.run(self.result)
        self.assertEqual(['setUp', 'foo'], self.test.log)

    def test_addCleanupCalledIfSetUpSkips(self):
        """
        Callables added with C{addCleanup} are run even if setUp raises
        L{SkipTest}. This allows test authors to reliably provide clean up
        code using C{addCleanup}.
        """
        self.test.setUp = self.test.skippingSetUp
        self.test.addCleanup(self.test.append, 'foo')
        self.test.run(self.result)
        self.assertEqual(['setUp', 'foo'], self.test.log)

    def test_addCleanupCalledInReverseOrder(self):
        """
        Callables added with C{addCleanup} should be called before C{tearDown}
        in reverse order of addition.
        """
        self.test.addCleanup(self.test.append, "foo")
        self.test.addCleanup(self.test.append, 'bar')
        self.test.run(self.result)
        self.assertEqual(['setUp', 'runTest', 'bar', 'foo', 'tearDown'],
                         self.test.log)

    def test_errorInCleanupIsCaptured(self):
        """
        Errors raised in cleanup functions should be treated like errors in
        C{tearDown}. They should be added as errors and fail the test. Skips,
        todos and failures are all treated as errors.
        """
        self.test.addCleanup(self.test.fail, 'foo')
        self.test.run(self.result)
        self.failIf(self.result.wasSuccessful())
        self.assertEqual(1, len(self.result.errors))
        [(test, error)] = self.result.errors
        self.assertEqual(test, self.test)
        self.assertEqual(error.getErrorMessage(), 'foo')

    def test_cleanupsContinueRunningAfterError(self):
        """
        If a cleanup raises an error then that does not stop the other
        cleanups from being run.
        """
        self.test.addCleanup(self.test.append, 'foo')
        self.test.addCleanup(self.test.fail, 'bar')
        self.test.run(self.result)
        self.assertEqual(['setUp', 'runTest', 'foo', 'tearDown'],
                         self.test.log)
        self.assertEqual(1, len(self.result.errors))
        [(test, error)] = self.result.errors
        self.assertEqual(test, self.test)
        self.assertEqual(error.getErrorMessage(), 'bar')

    def test_multipleErrorsReported(self):
        """
        If more than one cleanup fails, then the test should fail with more
        than one error.
        """
        self.test.addCleanup(self.test.fail, 'foo')
        self.test.addCleanup(self.test.fail, 'bar')
        self.test.run(self.result)
        self.assertEqual(['setUp', 'runTest', 'tearDown'],
                         self.test.log)
        self.assertEqual(2, len(self.result.errors))
        [(test1, error1), (test2, error2)] = self.result.errors
        self.assertEqual(test1, self.test)
        self.assertEqual(test2, self.test)
        self.assertEqual(error1.getErrorMessage(), 'bar')
        self.assertEqual(error2.getErrorMessage(), 'foo')


class SynchronousAddCleanupTests(AddCleanupMixin, unittest.SynchronousTestCase):
    """
    Test the addCleanup method of TestCase in the synchronous case

    See: L{twisted.trial.test.test_tests.AddCleanupMixin}
    """
    from twisted.trial.test.skipping import SynchronousAddCleanup as AddCleanup


class AsynchronousAddCleanupTests(AddCleanupMixin, unittest.TestCase):
    """
    Test the addCleanup method of TestCase in the asynchronous case

    See: L{twisted.trial.test.test_tests.AddCleanupMixin}
    """
    from twisted.trial.test.skipping import AsynchronousAddCleanup as AddCleanup

    def test_addCleanupWaitsForDeferreds(self):
        """
        If an added callable returns a L{Deferred}, then the test should wait
        until that L{Deferred} has fired before running the next cleanup
        method.
        """
        def cleanup(message):
            d = defer.Deferred()
            reactor.callLater(0, d.callback, message)
            return d.addCallback(self.test.append)
        self.test.addCleanup(self.test.append, 'foo')
        self.test.addCleanup(cleanup, 'bar')
        self.test.run(self.result)
        self.assertEqual(['setUp', 'runTest', 'bar', 'foo', 'tearDown'],
                         self.test.log)


class SuiteClearingMixin(object):
    """
    Tests for our extension that allows us to clear out a L{TestSuite}.
    """
    if _PY3:
        skip = _PY3PORTNEEDED

    def test_clearSuite(self):
        """
        Calling L{unittest._clearSuite} on a populated L{TestSuite} removes
        all tests.
        """
        suite = unittest.TestSuite()
        suite.addTest(self.TestCase())
        # Double check that the test suite actually has something in it.
        self.assertEqual(1, suite.countTestCases())
        unittest._clearSuite(suite)
        self.assertEqual(0, suite.countTestCases())


    def test_clearPyunitSuite(self):
        """
        Calling L{unittest._clearSuite} on a populated standard library
        L{TestSuite} removes all tests.

        This test is important since C{_clearSuite} operates by mutating
        internal variables.
        """
        pyunit = __import__('unittest')
        suite = pyunit.TestSuite()
        suite.addTest(self.TestCase())
        # Double check that the test suite actually has something in it.
        self.assertEqual(1, suite.countTestCases())
        unittest._clearSuite(suite)
        self.assertEqual(0, suite.countTestCases())


class SynchronousSuiteClearingTests(SuiteClearingMixin, unittest.SynchronousTestCase):
    """
    Tests for our extension that allows us to clear out a L{TestSuite} in the 
    synchronous case.

    See L{twisted.trial.test.test_tests.SuiteClearingMixin}
    """
    TestCase = unittest.SynchronousTestCase


class AsynchronousSuiteClearingTests(SuiteClearingMixin, unittest.TestCase):
    """
    Tests for our extension that allows us to clear out a L{TestSuite} in the 
    asynchronous case.

    See L{twisted.trial.test.test_tests.SuiteClearingMixin}
    """
    TestCase = unittest.TestCase


class TestDecoratorMixin(object):
    """
    Tests for our test decoration features.
    """
    if _PY3:
        skip = _PY3PORTNEEDED

    def assertTestsEqual(self, observed, expected):
        """
        Assert that the given decorated tests are equal.
        """
        self.assertEqual(observed.__class__, expected.__class__,
                         "Different class")
        observedOriginal = getattr(observed, '_originalTest', None)
        expectedOriginal = getattr(expected, '_originalTest', None)
        self.assertIdentical(observedOriginal, expectedOriginal)
        if observedOriginal is expectedOriginal is None:
            self.assertIdentical(observed, expected)

    def assertSuitesEqual(self, observed, expected):
        """
        Assert that the given test suites with decorated tests are equal.
        """
        self.assertEqual(observed.__class__, expected.__class__,
                         "Different class")
        self.assertEqual(len(observed._tests), len(expected._tests),
                         "Different number of tests.")
        for observedTest, expectedTest in zip(observed._tests,
                                              expected._tests):
            if getattr(observedTest, '_tests', None) is not None:
                self.assertSuitesEqual(observedTest, expectedTest)
            else:
                self.assertTestsEqual(observedTest, expectedTest)

    def test_usesAdaptedReporterWithRun(self):
        """
        For decorated tests, C{run} uses a result adapter that preserves the
        test decoration for calls to C{addError}, C{startTest} and the like.

        See L{reporter._AdaptedReporter}.
        """
        test = self.TestCase()
        decoratedTest = unittest.TestDecorator(test)
        # Move to top in ticket #5964:
        from twisted.trial.test.test_reporter import LoggingReporter
        result = LoggingReporter()
        decoratedTest.run(result)
        self.assertTestsEqual(result.test, decoratedTest)

    def test_usesAdaptedReporterWithCall(self):
        """
        For decorated tests, C{__call__} uses a result adapter that preserves
        the test decoration for calls to C{addError}, C{startTest} and the
        like.

        See L{reporter._AdaptedReporter}.
        """
        test = self.TestCase()
        decoratedTest = unittest.TestDecorator(test)
        # Move to top in ticket #5964:
        from twisted.trial.test.test_reporter import LoggingReporter
        result = LoggingReporter()
        decoratedTest(result)
        self.assertTestsEqual(result.test, decoratedTest)

    def test_decorateSingleTest(self):
        """
        Calling L{decorate} on a single test case returns the test case
        decorated with the provided decorator.
        """
        test = self.TestCase()
        decoratedTest = unittest.decorate(test, unittest.TestDecorator)
        self.assertTestsEqual(unittest.TestDecorator(test), decoratedTest)

    def test_decorateTestSuite(self):
        """
        Calling L{decorate} on a test suite will return a test suite with
        each test decorated with the provided decorator.
        """
        test = self.TestCase()
        suite = unittest.TestSuite([test])
        decoratedTest = unittest.decorate(suite, unittest.TestDecorator)
        self.assertSuitesEqual(
            decoratedTest, unittest.TestSuite([unittest.TestDecorator(test)]))

    def test_decorateInPlaceMutatesOriginal(self):
        """
        Calling L{decorate} on a test suite will mutate the original suite.
        """
        test = self.TestCase()
        suite = unittest.TestSuite([test])
        decoratedTest = unittest.decorate(
            suite, unittest.TestDecorator)
        self.assertSuitesEqual(
            decoratedTest, unittest.TestSuite([unittest.TestDecorator(test)]))
        self.assertSuitesEqual(
            suite, unittest.TestSuite([unittest.TestDecorator(test)]))

    def test_decorateTestSuiteReferences(self):
        """
        When decorating a test suite in-place, the number of references to the
        test objects in that test suite should stay the same.

        Previously, L{unittest.decorate} recreated a test suite, so the
        original suite kept references to the test objects. This test is here
        to ensure the problem doesn't reappear again.
        """
        getrefcount = getattr(sys, 'getrefcount', None)
        if getrefcount is None:
            raise unittest.SkipTest(
                "getrefcount not supported on this platform")
        test = self.TestCase()
        suite = unittest.TestSuite([test])
        count1 = getrefcount(test)
        decoratedTest = unittest.decorate(suite, unittest.TestDecorator)
        count2 = getrefcount(test)
        self.assertEqual(count1, count2)

    def test_decorateNestedTestSuite(self):
        """
        Calling L{decorate} on a test suite with nested suites will return a
        test suite that maintains the same structure, but with all tests
        decorated.
        """
        test = self.TestCase()
        suite = unittest.TestSuite([unittest.TestSuite([test])])
        decoratedTest = unittest.decorate(suite, unittest.TestDecorator)
        expected = unittest.TestSuite(
            [unittest.TestSuite([unittest.TestDecorator(test)])])
        self.assertSuitesEqual(decoratedTest, expected)

    def test_decorateDecoratedSuite(self):
        """
        Calling L{decorate} on a test suite with already-decorated tests
        decorates all of the tests in the suite again.
        """
        test = self.TestCase()
        decoratedTest = unittest.decorate(test, unittest.TestDecorator)
        redecoratedTest = unittest.decorate(decoratedTest,
                                            unittest.TestDecorator)
        self.assertTestsEqual(redecoratedTest,
                              unittest.TestDecorator(decoratedTest))

    def test_decoratePreservesSuite(self):
        """
        Tests can be in non-standard suites. L{decorate} preserves the
        non-standard suites when it decorates the tests.
        """
        test = self.TestCase()
        suite = runner.DestructiveTestSuite([test])
        decorated = unittest.decorate(suite, unittest.TestDecorator)
        self.assertSuitesEqual(
            decorated,
            runner.DestructiveTestSuite([unittest.TestDecorator(test)]))


class SynchronousTestDecoratorTests(TestDecoratorMixin, unittest.SynchronousTestCase):
    """
    Tests for our test decoration features in the synchronous case.

    See L{twisted.trial.test.test_tests.TestDecoratorMixin}
    """
    TestCase = unittest.SynchronousTestCase


class AsynchronousTestDecoratorTests(TestDecoratorMixin, unittest.TestCase):
    """
    Tests for our test decoration features in the asynchronous case.

    See L{twisted.trial.test.test_tests.TestDecoratorMixin}
    """
    TestCase = unittest.TestCase


class MonkeyPatchMixin(object):
    """
    Tests for the patch() helper method in L{unittest.TestCase}.
    """
    def setUp(self):
        """
        Setup our test case
        """
        self.originalValue = 'original'
        self.patchedValue = 'patched'
        self.objectToPatch = self.originalValue
        self.test = self.TestCase()

    def test_patch(self):
        """
        Calling C{patch()} on a test monkey patches the specified object and
        attribute.
        """
        self.test.patch(self, 'objectToPatch', self.patchedValue)
        self.assertEqual(self.objectToPatch, self.patchedValue)

    def test_patchRestoredAfterRun(self):
        """
        Any monkey patches introduced by a test using C{patch()} are reverted
        after the test has run.
        """
        self.test.patch(self, 'objectToPatch', self.patchedValue)
        self.test.run(reporter.Reporter())
        self.assertEqual(self.objectToPatch, self.originalValue)

    def test_revertDuringTest(self):
        """
        C{patch()} return a L{monkey.MonkeyPatcher} object that can be used to
        restore the original values before the end of the test.
        """
        patch = self.test.patch(self, 'objectToPatch', self.patchedValue)
        patch.restore()
        self.assertEqual(self.objectToPatch, self.originalValue)

    def test_revertAndRepatch(self):
        """
        The returned L{monkey.MonkeyPatcher} object can re-apply the patch
        during the test run.
        """
        patch = self.test.patch(self, 'objectToPatch', self.patchedValue)
        patch.restore()
        patch.patch()
        self.assertEqual(self.objectToPatch, self.patchedValue)

    def test_successivePatches(self):
        """
        Successive patches are applied and reverted just like a single patch.
        """
        self.test.patch(self, 'objectToPatch', self.patchedValue)
        self.assertEqual(self.objectToPatch, self.patchedValue)
        self.test.patch(self, 'objectToPatch', 'second value')
        self.assertEqual(self.objectToPatch, 'second value')
        self.test.run(reporter.Reporter())
        self.assertEqual(self.objectToPatch, self.originalValue)


class SynchronousMonkeyPatchTests(MonkeyPatchMixin, unittest.SynchronousTestCase):
    """
    Tests for the patch() helper method in the synchronous case.

    See L{twisted.trial.test.test_tests.MonkeyPatchMixin}
    """
    TestCase = unittest.SynchronousTestCase


class AsynchronousMonkeyPatchTests(MonkeyPatchMixin, unittest.TestCase):
    """
    Tests for the patch() helper method in the asynchronous case.

    See L{twisted.trial.test.test_tests.MonkeyPatchMixin}
    """
    TestCase = unittest.TestCase


class IterateTestsMixin(object):
    """
    L{_iterateTests} returns a list of all test cases in a test suite or test
    case.
    """
    if _PY3:
        skip = _PY3PORTNEEDED

    def test_iterateTestCase(self):
        """
        L{_iterateTests} on a single test case returns a list containing that
        test case.
        """
        test = self.TestCase()
        self.assertEqual([test], list(unittest._iterateTests(test)))


    def test_iterateSingletonTestSuite(self):
        """
        L{_iterateTests} on a test suite that contains a single test case
        returns a list containing that test case.
        """
        test = self.TestCase()
        suite = runner.TestSuite([test])
        self.assertEqual([test], list(unittest._iterateTests(suite)))


    def test_iterateNestedTestSuite(self):
        """
        L{_iterateTests} returns tests that are in nested test suites.
        """
        test = self.TestCase()
        suite = runner.TestSuite([runner.TestSuite([test])])
        self.assertEqual([test], list(unittest._iterateTests(suite)))


    def test_iterateIsLeftToRightDepthFirst(self):
        """
        L{_iterateTests} returns tests in left-to-right, depth-first order.
        """
        test = self.TestCase()
        suite = runner.TestSuite([runner.TestSuite([test]), self])
        self.assertEqual([test, self], list(unittest._iterateTests(suite)))


class SynchronousIterateTestsTests(IterateTestsMixin, unittest.SynchronousTestCase):
    """
    Check that L{_iterateTests} returns a list of all test cases in a test suite 
    or test case for synchronous tests.

    See L{twisted.trial.test.test_tests.IterateTestsMixin}
    """
    TestCase = unittest.SynchronousTestCase


class AsynchronousIterateTestsTests(IterateTestsMixin, unittest.TestCase):
    """
    Check that L{_iterateTests} returns a list of all test cases in a test suite 
    or test case for asynchronous tests.

    See L{twisted.trial.test.test_tests.IterateTestsMixin}
    """
    TestCase = unittest.TestCase
