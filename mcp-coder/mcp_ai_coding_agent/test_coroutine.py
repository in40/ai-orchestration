import asyncio

async def async_func():
    pass

def sync_func():
    pass

print("async_func is coroutine:", asyncio.iscoroutinefunction(async_func))
print("sync_func is coroutine:", asyncio.iscoroutinefunction(sync_func))