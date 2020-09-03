import sys
import os
import pyglet
import threading
from pyglet.window import key

from ctypes import c_ubyte, c_ushort
from typing import List
from random import randint

from fontset import chip8_fontset


class Chip8:
    def __init__(self, path=None, debug=False):
        self.memory: List[c_ubyte] = [
            0x0,
        ] * 4096
        self.V: List[c_ubyte] = [
            0x0,
        ] * 16
        self.I: c_ushort = 0
        self.pc: c_ushort = 0x200

        self.gfx: List[c_ubyte] = [
            0x0,
        ] * (64 * 32)
        self.keys: List[c_ubyte] = [
            0x0,
        ] * 16

        self.delay_timer: c_ubyte = 0x0
        self.sound_timer: c_ubyte = 0x0

        self.stack: List[c_ushort] = []

        self.draw_flag: bool = False
        self.blocked: bool = False
        self.blocked_x: c_ubyte = 0x0

        self.load_fontset()

        if path:
            self.load_rom(path)
        self.debug = debug

    def load_fontset(self):
        for i, font_byte in enumerate(chip8_fontset):
            self.memory[i] = font_byte

    def load_rom(self, path):
        self.path = path
        idx = 0x200
        with open(path, "rb") as rom:
            while idx < len(self.memory):
                next_byte = rom.read(1)
                self.memory[idx] = int.from_bytes(next_byte, byteorder="big")
                idx += 1

    def clear_screen(self):
        self.gfx: List[c_ubyte] = [
            0,
        ] * (64 * 32)

    def update_timers(self, dt):
        if self.delay_timer > 0:
            self.delay_timer -= 1

        if self.sound_timer > 0:
            if self.sound_timer == 1:
                print("BEEP!")
            self.sound_timer -= 1

    def step(self, _dt=None):
        if self.blocked:
            return
        opcode = self.fetch_opcode()
        if self.debug:
            print("OPCODE: [0x%02x]" % opcode)
        # if _dt:
        #     print("%s seconds elapsed since last step." % _dt)
        try:
            self.execute_opcode(opcode)
            assert all([vx < 256 for vx in self.V])
        except:
            print("OPCODE FAILED: [0x%02x]" % opcode)
            raise

    def run(self):
        window = pyglet.window.Window(640, 320, "[CHIP-8] %s" % self.path)
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
            for i, pixel in enumerate(self.gfx):
                if not pixel:
                    continue
                x = (i % 64) * 10
                y = (32 - (i // 64)) * 10 - 10
                batch.add(
                    4,
                    pyglet.gl.GL_QUADS,
                    None,
                    ("v2f", (x, y, x + width, y, x + width, y + height, x, y + height)),
                    ("c3B", FG_COLOR * 4),
                )
            batch.draw()
            # window.flip()

        def event_loop_thread(window):
            t = threading.currentThread()
            while not getattr(window, "closed", False):
                self.step()

        main_thread = threading.Thread(target=event_loop_thread, args=(window,))
        pyglet.clock.schedule(self.update_timers)

        @window.event
        def on_close():
            window.closed = True
            window.close()

        @window.event
        def on_draw():
            if self.draw_flag:
                draw_graphics()
                # self.draw_flag = False

        KEYS = {
            key._1: 0x0001,
            key._2: 0x0002,
            key._3: 0x0003,
            key._4: 0x000C,
            key.Q: 0x0004,
            key.W: 0x0005,
            key.E: 0x0006,
            key.R: 0x000D,
            key.A: 0x0007,
            key.S: 0x0008,
            key.D: 0x0009,
            key.F: 0x000E,
            key.Z: 0x000A,
            key.X: 0x0000,
            key.C: 0x000B,
            key.V: 0x000F,
        }

        @window.event
        def on_key_press(symbol, modifiers):
            if symbol in KEYS:
                self.keys[KEYS[symbol]] = 1
                if self.blocked:
                    self.V[self.blocked_x] = KEYS[symbol]
                    self.blocked = False

        @window.event
        def on_key_release(symbol, modifiers):
            if KEYS.get(symbol):
                self.keys[KEYS[symbol]] = 0

        main_thread.start()
        pyglet.app.run()

    def fetch_opcode(self):
        return self.memory[self.pc] << 8 | self.memory[self.pc + 1]

    def execute_opcode(self, opcode):
        if opcode == 0x00E0:
            # clear the screen
            self.clear_screen()
            self.pc += 2
            return
        elif opcode == 0x00EE:
            # return from subroutine
            self.pc = self.stack.pop() + 2
            return

        bits = opcode & 0xF000  # first four bits, which opcode (of family thereof)

        if bits == 0x1000:
            # goto
            self.pc = opcode & 0x0FFF
            return
        elif bits == 0x2000:
            # call subroutine
            self.stack.append(self.pc)
            self.pc = opcode & 0x0FFF
            return
        elif bits == 0x3000:
            # skip if equal to n
            vx = self.V[(opcode & 0x0F00) >> 8]
            if vx == opcode & 0x00FF:
                self.pc += 2
            self.pc += 2
            return
        elif bits == 0x4000:
            # skip if not equal to n
            vx = self.V[(opcode & 0x0F00) >> 8]
            if vx != opcode & 0x00FF:
                self.pc += 2
            self.pc += 2
            return
        elif bits == 0x5000:
            # skip if Vx == Vy
            vx = self.V[(opcode & 0x0F00) >> 8]
            vy = self.V[(opcode & 0x00F0) >> 4]
            if vx == vy:
                self.pc += 2
            self.pc += 2
            return
        elif bits == 0x6000:
            # set Vx to n
            self.V[(opcode & 0x0F00) >> 8] = opcode & 0x00FF
            self.pc += 2
            return
        elif bits == 0x7000:
            # add n to Vx (carry flag is unchanged)
            x = (opcode & 0x0F00) >> 8
            self.V[x] = (self.V[x] + opcode & 0x00FF) % 0xFFF
            self.pc += 2
            return
        elif bits == 0x8000:
            # do some math
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
            # skip if Vx != Vy
            vx = self.V[(opcode & 0x0F00) >> 8]
            vy = self.V[(opcode & 0x00F0) >> 4]
            if vx != vy:
                self.pc += 2
            self.pc += 2
            return
        elif bits == 0xA000:
            # set I to n
            self.I = opcode & 0x0FFF
            self.pc += 2
            return
        elif bits == 0xB000:
            # goto V0 + n
            self.pc = self.V[0] + (opcode & 0x0FFF)
            self.pc += 2
            return
        elif bits == 0xC000:
            # Vx = rand & n
            self.V[(opcode & 0x0F00) >> 8] = randint(0, 255) & (opcode & 0x00FF)
            self.pc += 2
            return
        elif bits == 0xD000:
            # draw sprite at (x,y) of height n
            x: c_ushort = self.V[(opcode & 0x0F00) >> 8] % 0xFFF
            y: c_ushort = self.V[(opcode & 0x00F0) >> 4] % 0xFFF
            height: c_ushort = opcode & 0x000F
            pixel: c_ushort = 0
            self.V[0xF] = 0
            for yline in range(height):
                pixel = self.memory[self.I + yline]
                for xline in range(8):
                    if pixel & (0x80 >> xline) != 0:
                        if self.gfx[x + xline + ((y + yline) * 64)] == 1:
                            self.V[0xF] = 1
                        self.gfx[x + xline + ((y + yline) * 64)] ^= 1
            self.draw_flag = True
            self.pc += 2
            return
        elif bits == 0xE000:
            # keyop
            x = (opcode & 0x0F00) >> 8
            if opcode & 0x00FF == 0x009E:
                # skip if key in Vx is pressed
                if self.keys[x]:
                    self.pc += 2
            elif opcode & 0x00FF == 0x00A1:
                # skip if key in Vx is not pressed
                if not self.keys[x]:
                    self.pc += 2
            self.pc += 2
            return
        elif bits == 0xF000:
            x = (opcode & 0x0F00) >> 8
            if opcode & 0x00FF == 0x0007:
                # set Vx = delay timer
                self.V[x] = self.delay_timer
            elif opcode & 0x00FF == 0x000A:
                # wait for keypress and store in Vx
                self.blocked = True
                self.blocked_x = x
            elif opcode & 0x00FF == 0x0015:
                # set delay timer = Vx
                self.delay_timer = self.V[x]
            elif opcode & 0x00FF == 0x0018:
                # set sound timer = Vx
                self.sound_timer = self.V[x]
            elif opcode & 0x00FF == 0x001E:
                if self.I + self.V[x] > 0xFFF:
                    self.V[0xF] = 1
                else:
                    self.V[0xF] = 0
                self.I = (self.I + self.V[x]) % 0xFFF
            elif opcode & 0x00FF == 0x0029:
                # set I to the loc of sprite character in Vx
                self.I = self.V[x] * 5
            elif opcode & 0x00FF == 0x0055:
                # dump V to memory
                offset = self.I
                for i in range(0, x + 1):
                    self.memory[offset] = self.V[i]
                    offset += 1
            elif opcode & 0x00FF == 0x0065:
                # load V from memory
                offset = self.I
                for i in range(0, x + 1):
                    self.V[i] = self.memory[offset]
                    offset += 1
            self.pc += 2
            return


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = "roms/Chip8 Picture.ch8"
    debug = int(os.environ.get("DEBUG", 0))
    Chip8(path, debug=debug).run()
