import trio

from oscpy.server.trio_server import OSCTrioServer


async def osc_app(address, port):
    osc = OSCTrioServer(encoding='utf8')
    await osc.listen(address=address, port=port, default=True)

    @osc.address("/example")
    async def example(*values):
        print(f"got {values} on /example")
        await trio.sleep(4)
        print("done sleeping")

    @osc.address("/test")
    async def test(*values):
        print(f"got {values} on /test")
        await trio.sleep(4)
        print("done sleeping")

    @osc.address("/stop")
    async def stop(*values):
        print(f"time to leave!")
        await osc.stop_all()

    @osc.address("/info")
    async def info():
        address, port = osc.getaddress()
        print(address, port)

    await osc.process()

trio.run(osc_app, '0.0.0.0', 8000)
