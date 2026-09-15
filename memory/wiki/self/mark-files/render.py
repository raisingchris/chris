#!/usr/bin/env python3
"""Rebuild PNGs using installed librsvg/Cairo shared libraries (no Python packages)."""
import argparse
import ctypes as C
import ctypes.util
import os
from pathlib import Path
import struct
import zlib

os.environ['OMP_NUM_THREADS'] = '2'
os.environ['RAYON_NUM_THREADS'] = '2'
from mark import svg


def library(name, signatures):
    lib = C.CDLL(ctypes.util.find_library(name))
    for function, result, arguments in signatures:
        f = getattr(lib, function)
        f.restype, f.argtypes = result, arguments
    return lib


class Rect(C.Structure):
    _fields_ = [(key, C.c_double) for key in ('x', 'y', 'width', 'height')]


def render(data, width, height, path):
    ptr, integer = C.c_void_p, C.c_int
    cairo = library('cairo', [
        ('cairo_image_surface_create', ptr, [integer, integer, integer]),
        ('cairo_create', ptr, [ptr]),
        ('cairo_surface_write_to_png', integer, [ptr, C.c_char_p]),
        ('cairo_destroy', None, [ptr]),
        ('cairo_surface_destroy', None, [ptr]),
    ])
    rsvg = library('rsvg-2', [
        ('rsvg_handle_new_from_data', ptr, [C.c_char_p, C.c_size_t, C.POINTER(ptr)]),
        ('rsvg_handle_render_document', integer, [ptr, ptr, C.POINTER(Rect), C.POINTER(ptr)]),
    ])
    gobject = library('gobject-2.0', [('g_object_unref', None, [ptr])])
    error = ptr()
    handle = rsvg.rsvg_handle_new_from_data(data, len(data), C.byref(error))
    if not handle:
        raise RuntimeError('librsvg could not parse SVG')
    surface = cairo.cairo_image_surface_create(0, width, height)
    context = cairo.cairo_create(surface)
    try:
        viewport = Rect(0, 0, width, height)
        if not rsvg.rsvg_handle_render_document(handle, context, C.byref(viewport), C.byref(error)):
            raise RuntimeError('librsvg rendering failed')
        if cairo.cairo_surface_write_to_png(surface, os.fsencode(path)):
            raise RuntimeError('Cairo PNG writing failed')
    finally:
        cairo.cairo_destroy(context)
        cairo.cairo_surface_destroy(surface)
        gobject.g_object_unref(handle)
    # SVG hex colours are sRGB. Record that interpretation explicitly in PNG.
    png = path.read_bytes()
    chunk = b'sRGB' + b'\x00'
    path.write_bytes(png[:33] + struct.pack('>I', 1) + chunk +
                     struct.pack('>I', zlib.crc32(chunk)) + png[33:])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('day', 'loops', 'loops-target', 'commits'):
        parser.add_argument('--' + name, type=int, required=True)
    parser.add_argument('--svg', type=Path, required=True, help='existing main SVG to render')
    parser.add_argument('--out-dir', type=Path, default=Path('.'))
    args = parser.parse_args()
    data = args.svg.read_bytes()
    for size in (512, 32):
        render(data, size, size, args.out_dir / f'mark-{size}.png')
    sheet = ['<svg xmlns="http://www.w3.org/2000/svg" width="1536" height="512" viewBox="0,0,1536,512">']
    for index, variant in enumerate(('seal', 'wide', 'compact')):
        mark = svg(args.day, args.loops, args.loops_target, args.commits, variant=variant)
        body = mark.split('\n', 1)[1].rsplit('</svg>', 1)[0]
        sheet.append(f'<g transform="translate({index * 512} 0)">{body}</g>')
    sheet.append('<text x="1512" y="488" text-anchor="end" font-family="DejaVu Sans" '
                 'font-size="12" letter-spacing="2" fill="#382D3B">SAMPLE</text></svg>')
    render(''.join(sheet).encode('utf-8'), 1536, 512, args.out_dir / 'variants.png')


if __name__ == '__main__':
    main()
