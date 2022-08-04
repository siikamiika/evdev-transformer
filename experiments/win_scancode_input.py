import ctypes
import json
import fileinput
import sys

# https://github.com/torvalds/linux/blob/master/include/uapi/linux/input-event-codes.h
EV_SYN = 0x00
EV_KEY = 0x01
EV_REL = 0x02
EV_ABS = 0x03

KEY_ESC = 1
KEY_1 = 2
KEY_2 = 3
KEY_3 = 4
KEY_4 = 5
KEY_5 = 6
KEY_6 = 7
KEY_7 = 8
KEY_8 = 9
KEY_9 = 10
KEY_0 = 11
KEY_MINUS = 12
KEY_EQUAL = 13
KEY_BACKSPACE = 14
KEY_TAB = 15
KEY_Q = 16
KEY_W = 17
KEY_E = 18
KEY_R = 19
KEY_T = 20
KEY_Y = 21
KEY_U = 22
KEY_I = 23
KEY_O = 24
KEY_P = 25
KEY_LEFTBRACE = 26
KEY_RIGHTBRACE = 27
KEY_ENTER = 28
KEY_LEFTCTRL = 29
KEY_A = 30
KEY_S = 31
KEY_D = 32
KEY_F = 33
KEY_G = 34
KEY_H = 35
KEY_J = 36
KEY_K = 37
KEY_L = 38
KEY_SEMICOLON = 39
KEY_APOSTROPHE = 40
KEY_GRAVE = 41
KEY_LEFTSHIFT = 42
KEY_BACKSLASH = 43
KEY_Z = 44
KEY_X = 45
KEY_C = 46
KEY_V = 47
KEY_B = 48
KEY_N = 49
KEY_M = 50
KEY_COMMA = 51
KEY_DOT = 52
KEY_SLASH = 53
KEY_RIGHTSHIFT = 54
KEY_KPASTERISK = 55
KEY_LEFTALT = 56
KEY_SPACE = 57
KEY_CAPSLOCK = 58
KEY_F1 = 59
KEY_F2 = 60
KEY_F3 = 61
KEY_F4 = 62
KEY_F5 = 63
KEY_F6 = 64
KEY_F7 = 65
KEY_F8 = 66
KEY_F9 = 67
KEY_F10 = 68
KEY_NUMLOCK = 69
KEY_SCROLLLOCK = 70
KEY_KP7 = 71
KEY_KP8 = 72
KEY_KP9 = 73
KEY_KPMINUS = 74
KEY_KP4 = 75
KEY_KP5 = 76
KEY_KP6 = 77
KEY_KPPLUS = 78
KEY_KP1 = 79
KEY_KP2 = 80
KEY_KP3 = 81
KEY_KP0 = 82
KEY_KPDOT = 83

KEY_ZENKAKUHANKAKU = 85
KEY_102ND = 86
KEY_F11 = 87
KEY_F12 = 88
KEY_RO = 89
KEY_KATAKANA = 90
KEY_HIRAGANA = 91
KEY_HENKAN = 92
KEY_KATAKANAHIRAGANA = 93
KEY_MUHENKAN = 94
KEY_KPJPCOMMA = 95
KEY_KPENTER = 96
KEY_RIGHTCTRL = 97
KEY_KPSLASH = 98
KEY_SYSRQ = 99
KEY_RIGHTALT = 100
KEY_LINEFEED = 101
KEY_HOME = 102
KEY_UP = 103
KEY_PAGEUP = 104
KEY_LEFT = 105
KEY_RIGHT = 106
KEY_END = 107
KEY_DOWN = 108
KEY_PAGEDOWN = 109
KEY_INSERT = 110
KEY_DELETE = 111
KEY_MACRO = 112
KEY_MUTE = 113
KEY_VOLUMEDOWN = 114
KEY_VOLUMEUP = 115
KEY_POWER = 116
KEY_KPEQUAL = 117
KEY_KPPLUSMINUS = 118
KEY_PAUSE = 119
KEY_SCALE = 120

KEY_KPCOMMA = 121
KEY_HANGEUL = 122
KEY_HANGUEL = KEY_HANGEUL
KEY_HANJA = 123
KEY_YEN = 124
KEY_LEFTMETA = 125
KEY_RIGHTMETA = 126
KEY_COMPOSE = 127

KEY_STOP = 128
KEY_AGAIN = 129
KEY_PROPS = 130
KEY_UNDO = 131
KEY_FRONT = 132
KEY_COPY = 133
KEY_OPEN = 134
KEY_PASTE = 135
KEY_FIND = 136
KEY_CUT = 137
KEY_HELP = 138
KEY_MENU = 139
KEY_CALC = 140
KEY_SETUP = 141
KEY_SLEEP = 142
KEY_WAKEUP = 143
KEY_FILE = 144
KEY_SENDFILE = 145
KEY_DELETEFILE = 146
KEY_XFER = 147
KEY_PROG1 = 148
KEY_PROG2 = 149
KEY_WWW = 150
KEY_MSDOS = 151
KEY_COFFEE = 152
KEY_SCREENLOCK = KEY_COFFEE
KEY_ROTATE_DISPLAY = 153
KEY_DIRECTION = KEY_ROTATE_DISPLAY
KEY_CYCLEWINDOWS = 154
KEY_MAIL = 155
KEY_BOOKMARKS = 156
KEY_COMPUTER = 157
KEY_BACK = 158
KEY_FORWARD = 159
KEY_CLOSECD = 160
KEY_EJECTCD = 161
KEY_EJECTCLOSECD = 162
KEY_NEXTSONG = 163
KEY_PLAYPAUSE = 164
KEY_PREVIOUSSONG = 165
KEY_STOPCD = 166
KEY_RECORD = 167
KEY_REWIND = 168
KEY_PHONE = 169
KEY_ISO = 170
KEY_CONFIG = 171
KEY_HOMEPAGE = 172
KEY_REFRESH = 173
KEY_EXIT = 174
KEY_MOVE = 175
KEY_EDIT = 176
KEY_SCROLLUP = 177
KEY_SCROLLDOWN = 178
KEY_KPLEFTPAREN = 179
KEY_KPRIGHTPAREN = 180
KEY_NEW = 181
KEY_REDO = 182

KEY_F13 = 183
KEY_F14 = 184
KEY_F15 = 185
KEY_F16 = 186
KEY_F17 = 187
KEY_F18 = 188
KEY_F19 = 189
KEY_F20 = 190
KEY_F21 = 191
KEY_F22 = 192
KEY_F23 = 193
KEY_F24 = 194

BTN_LEFT = 0x110
BTN_RIGHT = 0x111
BTN_MIDDLE = 0x112
BTN_SIDE = 0x113
BTN_EXTRA = 0x114

REL_X = 0x00
REL_Y = 0x01
REL_Z = 0x02
REL_RX = 0x03
REL_RY = 0x04
REL_RZ = 0x05
REL_HWHEEL = 0x06
REL_DIAL = 0x07
REL_WHEEL = 0x08
REL_MISC = 0x09

REL_WHEEL_HI_RES = 0x0b
REL_HWHEEL_HI_RES = 0x0c

# https://www.win.tue.nl/~aeb/linux/kbd/scancodes-1.html
# sc is almost the same as evdev KEY_* code
evdev_to_sc = {
    KEY_ESC: 0x01,
    KEY_1: 0x02,
    KEY_2: 0x03,
    KEY_3: 0x04,
    KEY_4: 0x05,
    KEY_5: 0x06,
    KEY_6: 0x07,
    KEY_7: 0x08,
    KEY_8: 0x09,
    KEY_9: 0x0a,
    KEY_0: 0x0b,
    KEY_MINUS: 0x0c,
    KEY_EQUAL: 0x0d,
    KEY_BACKSPACE: 0x0e,
    KEY_TAB: 0x0f,
    KEY_Q: 0x10,
    KEY_W: 0x11,
    KEY_E: 0x12,
    KEY_R: 0x13,
    KEY_T: 0x14,
    KEY_Y: 0x15,
    KEY_U: 0x16,
    KEY_I: 0x17,
    KEY_O: 0x18,
    KEY_P: 0x19,
    KEY_LEFTBRACE: 0x1a,
    KEY_RIGHTBRACE: 0x1b,
    KEY_ENTER: 0x1c,
    KEY_LEFTCTRL: 0x1d,
    KEY_A: 0x1e,
    KEY_S: 0x1f,
    KEY_D: 0x20,
    KEY_F: 0x21,
    KEY_G: 0x22,
    KEY_H: 0x23,
    KEY_J: 0x24,
    KEY_K: 0x25,
    KEY_L: 0x26,
    KEY_SEMICOLON: 0x27,
    KEY_APOSTROPHE: 0x28,
    KEY_GRAVE: 0x29,
    KEY_LEFTSHIFT: 0x2a,
    KEY_BACKSLASH: 0x2b,
    KEY_Z: 0x2c,
    KEY_X: 0x2d,
    KEY_C: 0x2e,
    KEY_V: 0x2f,
    KEY_B: 0x30,
    KEY_N: 0x31,
    KEY_M: 0x32,
    KEY_COMMA: 0x33,
    KEY_DOT: 0x34,
    KEY_SLASH: 0x35,
    KEY_RIGHTSHIFT: 0x36,
    KEY_KPASTERISK: 0x37,
    KEY_LEFTALT: 0x38,
    KEY_SPACE: 0x39,
    KEY_CAPSLOCK: 0x32,
    KEY_F1: 0x3b,
    KEY_F2: 0x3c,
    KEY_F3: 0x3d,
    KEY_F4: 0x3e,
    KEY_F5: 0x3f,
    KEY_F6: 0x40,
    KEY_F7: 0x41,
    KEY_F8: 0x42,
    KEY_F9: 0x43,
    KEY_F10: 0x44,
    KEY_NUMLOCK: 0x45,
    KEY_SCROLLLOCK: 0x46,
    KEY_KP7: 0x47,
    KEY_KP8: 0x48,
    KEY_KP9: 0x49,
    KEY_KPMINUS: 0x4a,
    KEY_KP4: 0x4b,
    KEY_KP5: 0x4c,
    KEY_KP6: 0x4d,
    KEY_KPPLUS: 0x4e,
    KEY_KP1: 0x4f,
    KEY_KP2: 0x50,
    KEY_KP3: 0x51,
    KEY_KP0: 0x52,
    KEY_KPDOT: 0x53,

    KEY_ZENKAKUHANKAKU: 0x55,
    KEY_102ND: 0x56,
    KEY_F11: 0x57,
    KEY_F12: 0x58,
    # TODO
    KEY_RO: 0x00,
    KEY_KATAKANA: 0x00,
    KEY_HIRAGANA: 0x00,
    KEY_HENKAN: 0x00,
    KEY_KATAKANAHIRAGANA: 0x00,
    KEY_MUHENKAN: 0x00,
    KEY_KPJPCOMMA: 0x00,
    KEY_KPENTER: 0x00,
    KEY_RIGHTCTRL: 0x00,
    KEY_KPSLASH: 0x00,
    KEY_SYSRQ: 0x00,
    KEY_RIGHTALT: 0x00,
    KEY_LINEFEED: 0x00,
    KEY_HOME: 0x00,
    KEY_UP: 0x00,
    KEY_PAGEUP: 0x00,
    KEY_LEFT: 0x00,
    KEY_RIGHT: 0x00,
    KEY_END: 0x00,
    KEY_DOWN: 0x00,
    KEY_PAGEDOWN: 0x00,
    KEY_INSERT: 0x00,
    KEY_DELETE: 0x00,
    KEY_MACRO: 0x00,
    KEY_MUTE: 0x00,
    KEY_VOLUMEDOWN: 0x00,
    KEY_VOLUMEUP: 0x00,
    KEY_POWER: 0x00,
    KEY_KPEQUAL: 0x00,
    KEY_KPPLUSMINUS: 0x00,
    KEY_PAUSE: 0x00,
    KEY_SCALE: 0x00,

    # TODO
    KEY_KPCOMMA: 0x00,
    KEY_HANGEUL: 0x00,
    KEY_HANGUEL: 0x00,
    KEY_HANJA: 0x00,
    KEY_YEN: 0x00,
    KEY_LEFTMETA: 0x00,
    KEY_RIGHTMETA: 0x00,
    KEY_COMPOSE: 0x00,

    # TODO
    KEY_STOP: 0x00,
    KEY_AGAIN: 0x00,
    KEY_PROPS: 0x00,
    KEY_UNDO: 0x00,
    KEY_FRONT: 0x00,
    KEY_COPY: 0x00,
    KEY_OPEN: 0x00,
    KEY_PASTE: 0x00,
    KEY_FIND: 0x00,
    KEY_CUT: 0x00,
    KEY_HELP: 0x00,
    KEY_MENU: 0x00,
    KEY_CALC: 0x00,
    KEY_SETUP: 0x00,
    KEY_SLEEP: 0x00,
    KEY_WAKEUP: 0x00,
    KEY_FILE: 0x00,
    KEY_SENDFILE: 0x00,
    KEY_DELETEFILE: 0x00,
    KEY_XFER: 0x00,
    KEY_PROG1: 0x00,
    KEY_PROG2: 0x00,
    KEY_WWW: 0x00,
    KEY_MSDOS: 0x00,
    KEY_COFFEE: 0x00,
    KEY_SCREENLOCK: 0x00,
    KEY_ROTATE_DISPLAY: 0x00,
    KEY_DIRECTION: 0x00,
    KEY_CYCLEWINDOWS: 0x00,
    KEY_MAIL: 0x00,
    KEY_BOOKMARKS: 0x00,
    KEY_COMPUTER: 0x00,
    KEY_BACK: 0x00,
    KEY_FORWARD: 0x00,
    KEY_CLOSECD: 0x00,
    KEY_EJECTCD: 0x00,
    KEY_EJECTCLOSECD: 0x00,
    KEY_NEXTSONG: 0x00,
    KEY_PLAYPAUSE: 0x00,
    KEY_PREVIOUSSONG: 0x00,
    KEY_STOPCD: 0x00,
    KEY_RECORD: 0x00,
    KEY_REWIND: 0x00,
    KEY_PHONE: 0x00,
    KEY_ISO: 0x00,
    KEY_CONFIG: 0x00,
    KEY_HOMEPAGE: 0x00,
    KEY_REFRESH: 0x00,
    KEY_EXIT: 0x00,
    KEY_MOVE: 0x00,
    KEY_EDIT: 0x00,
    KEY_SCROLLUP: 0x00,
    KEY_SCROLLDOWN: 0x00,
    KEY_KPLEFTPAREN: 0x00,
    KEY_KPRIGHTPAREN: 0x00,
    KEY_NEW: 0x00,
    KEY_REDO: 0x00,

    # TODO
    KEY_F13: 0x00,
    KEY_F14: 0x00,
    KEY_F15: 0x00,
    KEY_F16: 0x00,
    KEY_F17: 0x00,
    KEY_F18: 0x00,
    KEY_F19: 0x00,
    KEY_F20: 0x00,
    KEY_F21: 0x00,
    KEY_F22: 0x00,
    KEY_F23: 0x00,
    KEY_F24: 0x00,
}

# https://docs.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-mapvirtualkeyexw
MAPVK_VK_TO_VSC_EX = 4
MAPVK_VSC_TO_VK_EX = 3

# https://docs.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-mouse_event
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_MOVE = 0x0001

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010

MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040

MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100
XBUTTON1 = 0x0001
XBUTTON2 = 0x0002

MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000

user32 = ctypes.WinDLL('user32', use_last_error=True)

sc_to_vk = {}
for sc in range(0x100):
    sc_to_vk[sc] = user32.MapVirtualKeyExW(sc, MAPVK_VSC_TO_VK_EX, 0)
for vk in range(0x100):
    sc = user32.MapVirtualKeyExW(vk, MAPVK_VK_TO_VSC_EX, 0)
    if sc not in sc_to_vk:
        sc_to_vk[sc] = vk

def key_press(code, value):
    """
    code: int, evdev key code
    value: int, evdev key value (0 up, 1 down)
    """
    if BTN_LEFT <= code <= BTN_EXTRA:
        mouse_button_press(code, value)
    else:
        value_win = {
            0: 2,
            1: 0,
        }[value]
        sc = evdev_to_sc.get(code, 0)
        vk = sc_to_vk.get(sc, 0)
        user32.keybd_event(vk, sc, value_win, 0)

def mouse_button_press(code, value):
    """
    code: int, evdev key code
    value: int, evdev key value (0 up, 1 down)
    """
    code_win = {
        BTN_LEFT: (MOUSEEVENTF_LEFTUP, MOUSEEVENTF_LEFTDOWN),
        BTN_RIGHT: (MOUSEEVENTF_RIGHTUP, MOUSEEVENTF_RIGHTDOWN),
        BTN_MIDDLE: (MOUSEEVENTF_MIDDLEUP, MOUSEEVENTF_MIDDLEDOWN),
        BTN_SIDE: (MOUSEEVENTF_XUP, MOUSEEVENTF_XDOWN),
        BTN_EXTRA: (MOUSEEVENTF_XUP, MOUSEEVENTF_XDOWN),
    }[code][value]
    if code == BTN_SIDE:
        data = XBUTTON1
    elif code == BTN_EXTRA:
        data = XBUTTON2
    else:
        data = 0
    user32.mouse_event(code_win, 0, 0, data, 0)

def mouse_move_rel(x, y):
    """
    x: int, mouse move x axis
    y: int, mouse move y axis
    """
    user32.mouse_event(MOUSEEVENTF_MOVE, x, y, 0, 0)

def mouse_rotate_wheel(delta, axis):
    """
    delta: int, rotation amount
    axis: int, REL_WHEEL or REL_HWHEEL
    """
    axis_win = {
        REL_WHEEL: MOUSEEVENTF_WHEEL,
        REL_HWHEEL: MOUSEEVENTF_HWHEEL,
    }[axis]
    user32.mouse_event(axis_win, 0, 0, delta * 120, 0)

def interpret_evdev_events(events):
    """
    events: List[Dict[str, int]]
        .type: int, EV_KEY, EV_REL
        .code: int, KEY_*, REL_*
        .value: int
    """
    key_event = None
    rel_x_val = 0
    rel_y_val = 0
    rel_wheel_val = 0
    rel_hwheel_val = 0
    for event in events['events']:
        if event['type'] == EV_KEY:
            key_event = event
        elif event['type'] == EV_REL:
            if event['code'] == REL_X:
                rel_x_val += event['value']
            elif event['code'] == REL_Y:
                rel_y_val += event['value']
            elif event['code'] in {REL_WHEEL, REL_WHEEL_HI_RES}:
                rel_wheel_val += event['value']
            elif event['code'] in {REL_HWHEEL, REL_HWHEEL_HI_RES}:
                rel_hwheel_val += event['value']
        # TODO ABS
    if key_event:
        key_press(key_event['code'], key_event['value'])
    if rel_x_val or rel_y_val:
        mouse_move_rel(rel_x_val, rel_y_val)
    if rel_wheel_val:
        mouse_rotate_wheel(rel_wheel_val, REL_WHEEL)
    if rel_hwheel_val:
        mouse_rotate_wheel(rel_hwheel_val, REL_HWHEEL)

lines = fileinput.input()
# skip descriptor
next(lines)
for line in lines:
    events = json.loads(line)
    interpret_evdev_events(events)

# interpret_evdev_events([
#     {'type': EV_KEY, 'code': KEY_B, 'value': 1},
# ])
# interpret_evdev_events([
#     {'type': EV_KEY, 'code': KEY_B, 'value': 0},
# ])

# interpret_evdev_events([
#     {'type': EV_REL, 'code': REL_X, 'value': 123},
#     {'type': EV_REL, 'code': REL_Y, 'value': 123},
# ])

# interpret_evdev_events({'events': [
#     {'type': EV_KEY, 'code': BTN_LEFT, 'value': 1},
# ]})
# interpret_evdev_events({'events': [
#     {'type': EV_KEY, 'code': BTN_LEFT, 'value': 0},
# ]})
# exit()