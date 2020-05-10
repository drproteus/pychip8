# Chip-8 in Python

Chip-8 is the recommended system to begin emulator development on, and while Python might not be a recommended language, I wanted to see how feasible it is.

Resources used:
* http://www.multigesture.net/articles/how-to-write-an-emulator-chip-8-interpreter/
* https://en.wikipedia.org/wiki/CHIP-8#Virtual_machine_description

## Requirements
```
pyglet
```

## TODO
* Not all opcodes are implemented, some aren't implemented properly.
* Input is not handled
* Visualize stack, memory in separate window
* Load from menu, rather than just through CLI.

Despite the TODO, it does display GFX. Included is a `ch8` file displaying the IBM logo.

![screenshot](screenshots/ibm.png)