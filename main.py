import pyglet

from ctypes import c_uint, c_ubyte, c_ushort
from typing import List
from random import randint

from fontset import chip8_fontset


class Chip8:
    def __init__(self):
        self.memory: List[c_ubyte] = [0x0,] * 4096
        self.V: List[c_ubyte] = [0x0,] * 16
        self.I: c_ushort = 0
        self.pc: c_ushort = 0x200

        self.gfx: List[c_ubyte] = [0x0,] * (64 * 32)

        self.delay_timer: c_ubyte = 0x0
        self.sound_timer: c_ubyte = 0x0

        self.stack: List[c_ushort] = []

        self.draw_flag: bool = False

        self.load_fontset()

    def load_fontset(self):
        for i, font_byte in enumerate(chip8_fontset):
            self.memory[i] = font_byte

    def load_rom(self, path):
        idx = 0x200
        with open(path, "rb") as rom:
            while idx < len(self.memory):
                next_byte = rom.read(1)
                self.memory[idx] = int.from_bytes(next_byte, byteorder="big")
                idx += 1

    def clear_screen(self):
        self.gfx: List[c_ubyte] = [0,] * (64 * 32)

    def update_timers(self):
        if self.delay_timer > 0:
            self.delay_timer -= 1

        if self.sound_timer > 0:
            if self.sound_timer == 1:
                print("BEEP!")
            self.sound_timer -= 1

    def step(self, _dt=None):
        opcode = self.fetch_opcode()
        print("OPCODE: [0x%02x]" % opcode)
        if _dt:
            print("%s seconds elapsed since last step." % _dt)
        try:
            self.execute_opcode(opcode)
        except:
            print("OPCODE FAILED: [0x%02x]" % opcode)
            raise
        self.update_timers()

    def run(self):
        while True:
            pyglet.clock.tick()
            self.step()
            window.dispatch_events()
            if self.draw_flag:
                window.dispatch_event("on_draw")
            window.flip()

    def fetch_opcode(self):
        return self.memory[self.pc] << 8 | self.memory[self.pc + 1]

    def execute_opcode(self, opcode):
        if opcode == 0x00E0:
            self.clear_screen()
            self.pc += 2
            return
        elif opcode == 0x00EE:
            self.pc = self.stack.pop() + 2
            return

        bits = opcode & 0xF000  # first four bits, which opcode (of family thereof)

        if bits == 0x1000:
            self.pc = opcode & 0x0FFF
            return
        elif bits == 0x2000:
            self.stack.append(self.pc)
            self.pc = opcode & 0x0FFF
            return
        elif bits == 0x3000:
            vx = self.V[opcode & 0x0F00]
            if vx == opcode & 0x00FF:
                self.pc += 2
            self.pc += 2
            return
        elif bits == 0x4000:
            vx = self.V[opcode & 0x0F00]
            if vx != opcode & 0x00FF:
                self.pc += 2
            self.pc += 2
            return
        elif bits == 0x5000:
            vx = self.V[opcode & 0x0F00]
            vy = self.V[opcode & 0x00F0]
            if vx == vy:
                self.pc += 2
            self.pc += 2
            return
        elif bits == 0x6000:
            self.V[(opcode & 0x0F00) >> 8] = opcode & 0x00FF
            self.pc += 2
            return
        elif bits == 0x7000:
            self.V[(opcode & 0x0F00) >> 8] += opcode & 0x00FF  # carry flag is unchanged
            self.pc += 2
            return
        elif bits == 0x8000:
            math_bit = opcode & 0x000F
            x = (opcode & 0x0F00) >> 8
            y = (opcode & 0x00F0) >> 4
            if math_bit == 0x0000:
                self.V[x] = self.V[y]
            elif math_bit == 0x0001:
                self.V[x] = self.V[x] | self.V[y]
            elif math_bit == 0x0002:
                self.V[x] = self.V[x] & self.V[y]
            elif math_bit == 0x0003:
                self.V[x] = self.V[x] ^ self.V[y]
            elif math_bit == 0x0004:
                self.V[x] = self.V[x] + self.V[y]
            elif math_bit == 0x0005:
                self.V[x] = self.V[x] - self.V[y]
            elif math_bit == 0x0006:
                self.V[x] = self.V[x] >> 1
            elif math_bit == 0x0007:
                self.V[x] = self.V[y] - self.V[x]
            elif math_bit == 0x000E:
                self.V[x] = self.V[x] << 1
            self.pc += 2
            return
        elif bits == 0x9000:
            vx = self.V[(opcode & 0x0F00) >> 8]
            vy = self.V[(opcode & 0x00F0) >> 4]
            if vx != vy:
                self.pc += 2
                pass
            self.pc += 2
            return
        elif bits == 0xA000:
            self.I = opcode & 0x0FFF
            self.pc += 2
            return
        elif bits == 0xB000:
            self.pc = self.V[0] + (opcode & 0x0FFF)
            return
        elif bits == 0xC000:
            self.V[opcode & 0x0F00] = randint(0, 255) & (opcode & 0x00FF)
            return
        elif bits == 0xD000:
            x: c_ushort = self.V[(opcode & 0x0F00) >> 8]
            y: c_ushort = self.V[(opcode & 0x00F0) >> 4]
            height: c_ushort = opcode & 0x000F
            pixel: c_ushort = 0
            self.V[0xF] = 0
            for yline in range(height):
                pixel = self.memory[self.I + yline]
                for xline in range(8):
                    if pixel & (0x80 >> xline) != 0:
                        if self.gfx[x + xline + ((y + yline) * 64)] == 1:
                            V[0xF] = 1
                        self.gfx[x + xline + ((y + yline) * 64)] ^= 1
            self.draw_flag = True
            self.pc += 2
            return


if __name__ == "__main__":
    c = Chip8()
    path = "roms/IBM Logo.ch8"
    c.load_rom(path)

    window = pyglet.window.Window(640, 320, "[CHIP-8] %s" % path)
    event_loop = pyglet.app.EventLoop()

    FG_COLOR = (255, 130, 25)

    def draw_rect(x, y, color, width, height):
        batch = pyglet.graphics.Batch()
        pyglet.gl.glClear(pyglet.gl.GL_COLOR_BUFFER_BIT)
        pyglet.graphics.draw(
            4,
            pyglet.gl.GL_QUADS,
            ("v2f", [x, y, x + width, y, x + width, y + height, x, y + height]),
            ("c3B", color * 4),
        )

    def draw_graphics():
        batch = pyglet.graphics.Batch()
        pyglet.gl.glClear(pyglet.gl.GL_COLOR_BUFFER_BIT)
        height, width = 10, 10
        for i, pixel in enumerate(c.gfx):
            if not pixel:
                continue
            x = (i % 64) * 10
            y = (32 - (i // 64)) * 10
            batch.add(4, pyglet.gl.GL_QUADS, None,
                ("v2f", (x, y, x + width, y, x + width, y + height, x, y + height)),
                ("c3B", FG_COLOR * 4),
            )
        batch.draw()

    pyglet.clock.schedule(c.step)

    @window.event
    def on_draw():
        draw_graphics()
        pass

    pyglet.app.run()
