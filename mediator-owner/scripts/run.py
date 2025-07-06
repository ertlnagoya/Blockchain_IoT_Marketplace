import asyncio
import os

async def run_command(label, cmd, cwd):
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )

    async def read_stream(stream, prefix):
        while True:
            line = await stream.readline()
            if not line:
                break
            print(f"[{label}|{prefix}] {line.decode().rstrip()}")

    await asyncio.gather(
        read_stream(process.stdout, "OUT"),
        read_stream(process.stderr, "ERR"),
    )
    await process.wait()

async def main():
    cwd = os.path.join(os.path.dirname(__file__), "../")
    commands = [
        (f"owner-{i}", ["./target/debug/mediator-b", f"settings/owner_{i}.yaml"])
        for i in range(1, 12)
    ]

    await asyncio.gather(*(run_command(label, cmd, cwd) for label, cmd in commands))

if __name__ == "__main__":
    asyncio.run(main())
