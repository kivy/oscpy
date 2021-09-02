import curio

from oscpy.server.curio_server import OSCCurioServer


async def osc_app(address, port):
    osc = OSCCurioServer(encoding='utf8')
    osc.listen(address=address, port=port, default=True)

    @osc.address("/example")
    async def example(*values):
        print(f"got {values} on /example")
        await curio.sleep(4)
        print("done sleeping")

    @osc.address("/test")
    async def test(*values):
        print(f"got {values} on /test")
        await curio.sleep(4)
        print("done sleeping")

    @osc.address("/stop")
    async def stop(*values):
        print(f"time to leave!")
        await osc.stop_all()

    await osc.process()

curio.run(osc_app, '0.0.0.0', 8000)
