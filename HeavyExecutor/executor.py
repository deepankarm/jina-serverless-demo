import time

from jina import DocumentArray, Executor, requests


class HeavyExecutor(Executor):
    @requests
    def foo(self, docs: DocumentArray, **kwargs):
        time.sleep(3)
