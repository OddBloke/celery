from celery.worker.heartbeat import Heart

from celery.tests.utils import unittest, sleepdeprived


class MockDispatcher(object):
    heart = None
    next_iter = 0

    def __init__(self):
        self.sent = []

    def send(self, msg, **_fields):
        self.sent.append(msg)
        if self.heart:
            if self.next_iter > 10:
                self.heart._shutdown.set()
            self.next_iter += 1


class MockDispatcherRaising(object):

    def send(self, msg):
        if msg == "worker-offline":
            raise Exception("foo")


class MockTimer(object):

    def apply_interval(self, msecs, fun, args=(), kwargs={}):

        class entry(tuple):
            cancelled = False

            def cancel(self):
                self.cancelled = True

        return entry((msecs, fun, args, kwargs))

    def cancel(self, entry):
        entry.cancel()


class TestHeart(unittest.TestCase):

    def test_stop(self):
        timer = MockTimer()
        eventer = MockDispatcher()
        h = Heart(timer, eventer, interval=1)
        h.start()
        self.assertTrue(h.tref)
        h.stop()
        self.assertIsNone(h.tref)

    @sleepdeprived
    def test_run_manages_cycle(self):
        eventer = MockDispatcher()
        heart = Heart(MockTimer(), eventer, interval=0.1)
        eventer.heart = heart
        heart.start()
        msecs, fun, args, kwargs = tref = heart.tref
        self.assertEqual(msecs, 0.1 * 1000)
        self.assertEqual(tref.fun, eventer.send)
        self.assertTrue(tref.args)
        self.assertTrue(tref.kwargs)
        heart.stop()
        self.assertTrue(tref.cancelled)