import asyncio

import aiohttp
from aiohttp import FormData


async def upload_file(
        url: str,
        filepath: str
):
    data = FormData(quote_fields=True)
    data.add_field(
        'file',
        open(filepath, 'rb')
    )
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as response:
            print(await response.text())
            print(response.status)


def main():
    tasks = []

    for i in range(0, 10):
        tasks.append(
            upload_file(
                url="url",
                filepath="filepath",
            )
        )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(asyncio.gather(*tasks))
    print(result)
    loop.close()

main()





