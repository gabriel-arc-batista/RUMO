"""Capture only the selected native window, even behind other applications."""

import ctypes
from ctypes import wintypes
from PIL import Image


def capture_window(hwnd, path):
    user = ctypes.windll.user32
    gdi = ctypes.windll.gdi32
    user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.GetWindowDC.argtypes = [wintypes.HWND]
    user.GetWindowDC.restype = wintypes.HDC
    user.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    gdi.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi.CreateCompatibleDC.restype = wintypes.HDC
    gdi.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    gdi.CreateCompatibleBitmap.restype = wintypes.HBITMAP
    gdi.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi.SelectObject.restype = wintypes.HGDIOBJ
    gdi.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi.DeleteDC.argtypes = [wintypes.HDC]
    gdi.GetDIBits.argtypes = [
        wintypes.HDC,
        wintypes.HBITMAP,
        wintypes.UINT,
        wintypes.UINT,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.UINT,
    ]
    rect = wintypes.RECT()
    assert user.GetWindowRect(hwnd, ctypes.byref(rect))
    width, height = rect.right - rect.left, rect.bottom - rect.top

    class Header(ctypes.Structure):
        _fields_ = [
            ("size", wintypes.DWORD),
            ("width", wintypes.LONG),
            ("height", wintypes.LONG),
            ("planes", wintypes.WORD),
            ("bits", wintypes.WORD),
            ("compression", wintypes.DWORD),
            ("image_size", wintypes.DWORD),
            ("x", wintypes.LONG),
            ("y", wintypes.LONG),
            ("used", wintypes.DWORD),
            ("important", wintypes.DWORD),
        ]

    dc = user.GetWindowDC(hwnd)
    memory = gdi.CreateCompatibleDC(dc)
    bitmap = gdi.CreateCompatibleBitmap(dc, width, height)
    old = gdi.SelectObject(memory, bitmap)
    try:
        assert user.PrintWindow(hwnd, memory, 2), "Native window capture failed"
        gdi.SelectObject(memory, old)
        header = Header()
        header.size = ctypes.sizeof(Header)
        header.width = width
        header.height = -height
        header.planes = 1
        header.bits = 32
        pixels = ctypes.create_string_buffer(width * height * 4)
        assert (
            gdi.GetDIBits(dc, bitmap, 0, height, pixels, ctypes.byref(header), 0)
            == height
        )
        Image.frombytes("RGB", (width, height), pixels.raw, "raw", "BGRX").save(path)
    finally:
        gdi.SelectObject(memory, old)
        gdi.DeleteObject(bitmap)
        gdi.DeleteDC(memory)
        user.ReleaseDC(hwnd, dc)


def capture_tk_window(window, path):
    """Capture only this Tk window on Windows or X11."""
    import os

    if os.name == "nt":
        parent = ctypes.windll.user32.GetParent
        parent.argtypes = [ctypes.c_void_p]
        parent.restype = ctypes.c_void_p
        capture_window(parent(window.winfo_id()), path)
        return
    from Xlib import X, display

    connection = display.Display()
    try:
        wid = int(window.wm_frame(), 16) if window.wm_frame() else window.winfo_id()
        native = connection.create_resource_object("window", wid)
        geometry = native.get_geometry()
        raw = native.get_image(
            0, 0, geometry.width, geometry.height, X.ZPixmap, 0xFFFFFFFF
        )
        Image.frombytes(
            "RGB", (geometry.width, geometry.height), raw.data, "raw", "BGRX"
        ).save(path)
    finally:
        connection.close()
