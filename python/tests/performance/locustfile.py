import uuid
from locust import HttpUser, task, between

class MorkUser(HttpUser):
    wait_time = between(1, 5)
    host = "http://127.0.0.1:8000"

    def on_start(self):
        """ on_start is called when a Locust start before any task is scheduled """
        self.expr = str(uuid.uuid4())  # some random expression
        self.client.get(f"/busywait/1000?expr1={self.expr}&writer1=true", name="/busywait/[ms]")


    def on_stop(self):
        """ on_stop is called when the TaskSet is stopping """
        pass

    @task
    def status_poll(self):
        # This task simulates polling the /status endpoint.
        # We need a valid expression to check the status of.
        # For now, we'll use a placeholder.
        # In a real scenario, this would be an expression
        # that is being processed.
        self.client.get(f"/status/{self.expr}", name="/status/[expr]")

    @task
    def status_stream(self):
        # This task simulates listening to the /status_stream endpoint.
        # As with the polling task, we need a valid expression.
        with self.client.get(f"/status_stream/{self.expr}", stream=True, name="/status_stream/[expr]") as r:
            for line in r.iter_lines():
                if line:
                    # In a real test, you might want to assert
                    # the content of the SSE messages.
                    pass
