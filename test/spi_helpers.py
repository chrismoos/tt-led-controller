from dataclasses import dataclass
from cocotb.triggers import Timer, FallingEdge, RisingEdge, First


@dataclass
class SPIMasterConfig:
    clock_period: float = 0.00001
    ss_delay: float = clock_period * 2


class SPIMaster:
    def __init__(self, sck, mosi, miso, ss_n, config: SPIMasterConfig):
        self.sck = sck
        self.mosi = mosi
        self.miso = miso
        self.ss_n = ss_n
        self.sck.value = 0
        self.mosi.value = 0
        self.ss_n.value = 1
        self.config = config

    async def write(self, data):
        await Timer(self.config.ss_delay, 'sec')
        self.ss_n.value = 0
        self.sck.value = 0
        await Timer(self.config.ss_delay, 'sec')

        for byte in data:
            for x in range(0, 8):
                self.mosi.value = (byte >> (7 - x)) & 1
                await Timer(self.config.clock_period / 2.0, 'sec')
                self.sck.value = 1
                await Timer(self.config.clock_period / 2.0, 'sec')
                self.sck.value = 0

        await Timer(self.config.ss_delay, 'sec')
        self.ss_n.value = 1

    async def read(self, reg_addr, num_bytes):
        """Read registers starting at reg_addr."""
        self.ss_n.value = 0
        self.sck.value = 0
        await Timer(self.config.ss_delay, 'sec')

        # Send register address (read mode, no 0x80 bit)
        for x in range(0, 8):
            self.mosi.value = (reg_addr >> (7 - x)) & 1
            await Timer(self.config.clock_period / 2.0, 'sec')
            self.sck.value = 1
            await Timer(self.config.clock_period / 2.0, 'sec')
            self.sck.value = 0

        # Read response bytes
        result = []
        for _ in range(num_bytes):
            byte = 0
            for x in range(0, 8):
                self.mosi.value = 0
                await Timer(self.config.clock_period / 2.0, 'sec')
                self.sck.value = 1
                byte = (byte << 1) | int(self.miso.value)
                await Timer(self.config.clock_period / 2.0, 'sec')
                self.sck.value = 0
            result.append(byte)

        await Timer(self.config.ss_delay, 'sec')
        self.ss_n.value = 1
        return result


class SPISlave:
    STATE_IDLE = 1

    def __init__(self, sck, mosi, miso, ss_n):
        self.sck = sck
        self.mosi = mosi
        self.miso = miso
        self.ss_n = ss_n
        self.state = SPISlave.STATE_IDLE

    async def handle_data(self, byte):
        return 0

    async def end_transaction(self):
        pass

    async def run(self):
        while True:
            await FallingEdge(self.ss_n)
            num_read = 0
            data = 0
            miso = 0
            while True:
                await First(RisingEdge(self.sck), RisingEdge(self.ss_n))
                if self.ss_n.value:
                    break

                data <<= 1
                data |= int(self.mosi.value)
                num_read += 1
                if num_read == 8:
                    miso = await self.handle_data(data)
                    data = 0
                    num_read = 0

                # shift out next data byte on miso
                await First(FallingEdge(self.sck), RisingEdge(self.ss_n))
                if self.ss_n.value:
                    break
                self.miso.value = (miso >> 7) & 1
                miso <<= 1
            await self.end_transaction()
            miso = 0


class FlashSPI(SPISlave):
    STATE_INSTRUCTION = 1
    STATE_ADDRESS_HI = 2
    STATE_ADDRESS_LO = 3

    def __init__(self, sck, mosi, miso, ss_n, data):
        super().__init__(sck, mosi, miso, ss_n)
        self.data = data
        self.state = FlashSPI.STATE_INSTRUCTION
        self.address = 0

    async def end_transaction(self):
        self.state = FlashSPI.STATE_INSTRUCTION

    async def handle_data(self, byte):
        if self.state == FlashSPI.STATE_INSTRUCTION and byte == 3:
            self.state = FlashSPI.STATE_ADDRESS_HI
            self.address = 0
            assert byte == 3
        elif self.state == FlashSPI.STATE_ADDRESS_HI:
            self.address = byte << 8
            self.state = FlashSPI.STATE_ADDRESS_LO
        elif self.state == FlashSPI.STATE_ADDRESS_LO:
            self.address |= byte
            if self.address >= len(self.data):
                val = 0
            else:
                val = self.data[self.address]
            self.address += 1
            return val

        return 0
