import json
import uuid
from locust import HttpUser, task, between, events
import requests

SHARED_EXPR = None

@events.test_start.add_listener
def on_test_init(environment, **_kwargs):
    """
    This function is called once when Locust is initialized.
    It starts a single task on the server and stores the expression in a global variable.
    This ensures that all users share the same task.
    """
    global SHARED_EXPR
    ms = (1000 * 60 * 2) + (10000)  # 2 minutes + 10s possible delays
    expr = str(uuid.uuid4())
    print("locust init")
    # We need to use a separate requests session here because this is not running in a user context
    try:
        response = requests.get(f"http://127.0.0.1:8000/busywait/{ms}?expr1={expr}", timeout=10)
        response.raise_for_status()
        print("expr: ", expr)
        SHARED_EXPR = expr
    except requests.exceptions.RequestException as e:
        print(f"Failed to start shared task: {e}")
        # Stop the test if we can't start the shared task
        environment.runner.quit()


class CommonStatusUser(HttpUser):
    wait_time = between(1, 5)
    host = "http://127.0.0.1:8000"
    abstract = True
    _max_status_count = 20


    def start_task_on_server(self, ms=1000):
        expr = str(uuid.uuid4())  # some random expression
        self.client.get(f"/busywait/{ms}?expr1={expr}", name="/busywait/[ms]")
        return expr


    def get_unique_task(self):
        return SHARED_EXPR


    def on_start(self):
        self.status_count = 0

    def is_finished(self):
        if self.status_count >= self._max_status_count:
            print(f"({self.__class__.__name__}) status count max reached")
            return True

    def start_stream(self, expr):
        with self.client.get(f"/status_stream/{expr}", stream=True, name="/status_stream/[expr]") as r:
            for line in r.iter_lines():
                if line:
                    data_b = line.decode("utf-8")

                    if data_b.startswith("data:"):
                        json_part = data_b[len("data:"):].strip()
                        try:
                            data = json.loads(json_part)

                            if data["status"] == "pathClear":
                                self.status_count += 1
                                break
                        except json.JSONDecodeError as e:
                            print("Failed to decode JSON:", json_part, e)


    def start_poll(self, expr):
        is_finished = False

        while is_finished == False:
            response = self.client.get(f"/status/{expr}", name="/status/[expr]")
            data = response.json()

            if data["status"] == "pathClear":
                self.status_count += 1
                is_finished = True


class PollingUser(CommonStatusUser):
    @task
    def status(self):
        
        # put cap on status checks
        if self.is_finished():
            return

        expr = self.start_task_on_server()

        self.start_poll(expr)


class StreamingUser(CommonStatusUser):
    @task
    def status(self):

        # put cap on status checks
        if self.is_finished():
            return

        expr = self.start_task_on_server()

        self.start_stream(expr)


class MaxPollingUser(CommonStatusUser):
    @task
    def status(self):
        expr = self.get_unique_task()

        self.start_poll(expr)


class MaxStreamingUser(CommonStatusUser):
    @task
    def status(self):
        expr = self.get_unique_task()
       
        self.start_stream(expr)
