import anyio
async def run_sync(func, *args, **kwargs):
    return await anyio.to_thread.run_sync(lambda: func(*args, **kwargs))
