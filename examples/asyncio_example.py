import asyncio

from oscpy.server.asyncio_server import OSCAsyncioServer


async def osc_app(address, port):
    osc = OSCAsyncioServer(encoding='utf8')
    osc.listen(address=address, port=port, default=True)

    @osc.address("/example")
    async def example(*values):
        print(f"got {values} on /example")
        await asyncio.sleep(4)
        print("done sleeping")

    @osc.address("/test")
    async def test(*values):
        print(f"got {values} on /test")
        await asyncio.sleep(4)
        print("done sleeping")

    @osc.address("/stop")
    async def stop(*values):
        print(f"time to leave!")
        osc.terminate_server()

    asyncio.get_event_loop().create_task(osc.process())
    await osc.join_server()


asyncio.run(osc_app('localhost', 8000))
