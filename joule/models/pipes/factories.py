import asyncio


def reader_factory(fd, loop: asyncio.AbstractEventLoop):

    async def f():
        reader = asyncio.StreamReader()
        reader_protocol = asyncio.StreamReaderProtocol(reader)
        src = open(fd, 'rb')
        (transport, _) = await loop.connect_read_pipe(
            lambda: reader_protocol, src)
        return reader

    return f


def writer_factory(fd, loop: asyncio.AbstractEventLoop):

    async def f():
        write_protocol = asyncio.StreamReaderProtocol(asyncio.StreamReader())
        dest = open(fd, 'wb')
        (transport, _) = await loop.connect_write_pipe(
            lambda: write_protocol, dest)
        writer = asyncio.StreamWriter(
            transport, write_protocol, None, loop)
        return writer

    return f
