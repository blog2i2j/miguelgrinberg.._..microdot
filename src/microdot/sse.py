import asyncio
import json


class SSE:
    def __init__(self):
        self.event = asyncio.Event()
        self.queue = []
        self.closed = False

    async def send(self, data, event=None):
        if self.closed:
            raise OSError(32, 'Broken pipe')
        if isinstance(data, (dict, list)):
            data = json.dumps(data)
        data = f'data: {data}\n\n'
        if event:
            data = f'event: {event}\n{data}'
        self.queue.append(data)
        self.event.set()

    async def events(self):
        while not self.closed:
            await self.event.wait()
            self.event.clear()
            queue = self.queue
            self.queue = []
            for event in queue:
                yield event


def with_sse(f):
    """Decorator to make a route a Server-Side Events endpoint.

    This decorator is used to define a route that accepts SSE connections. The
    route then receives a sse object as a second argument that it can use to
    send events to the client::

        @app.route('/events')
        @with_sse
        async def echo(request, sse):
            for i in range(10):
                await asyncio.sleep(1)
                await sse.send(f'{i}')
    """
    async def sse_handler(*args, **kwargs):
        sse = SSE()

        async def route():
            await f(*args, sse, **kwargs)
            sse.closed = True

        async def sse_loop():
            task = asyncio.ensure_future(f(*args, sse, **kwargs))
            async for event in sse.events():
                yield event
            task.cancel()

        return sse_loop(), 200, {'Content-Type': 'text/event-stream'}
    return sse_handler
