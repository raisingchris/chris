#!/usr/bin/env python3
"""A numeric seal. Python 3.11+, standard library only."""
import argparse
import math
from pathlib import Path


PALETTES = {
    'seal': ('#F4EFE4', '#242B2B', '#B34F32'),
    'wide': ('#F3ECDD', '#25364A', '#A65A20'),
    'compact': ('#F0E8E0', '#382D3B', '#387367'),
}


def svg(day, loops, loops_target, commits, mono=False, variant='seal'):
    if not 0 <= day <= 10000:
        raise ValueError('day must be between 0 and 10000')
    if not 1 <= loops_target <= 10000 or not 0 <= loops <= loops_target:
        raise ValueError('require 0 <= loops <= loops-target <= 10000; target > 0')
    if commits < 0:
        raise ValueError('commits must be nonnegative')
    paper, ink, accent = PALETTES[variant]
    if mono:
        accent = ink
    inner_radius = {'seal': 104, 'wide': 132, 'compact': 76}[variant]
    # Day dots grow inward in rings of at most 24; the first ring holds day 1–24.
    rings = max(1, math.ceil(day / 24))
    radial_step = min(22, inner_radius / rings)
    dot_radius = min(9, radial_step * 0.4)
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">',
        f'  <rect width="512" height="512" fill="{paper}"/>',
        f'  <g id="ticks" stroke-linecap="round" data-count="{loops_target}">',
    ]
    for i in range(loops_target):
        closed = i < loops
        angle = -90 + 360 * i / loops_target
        start = 176 if closed else 184
        width = 10 if closed else 5
        color = accent if closed else ink
        lines.append(
            f'    <line id="tick-{i + 1}" class="tick {"closed" if closed else "open"}" '
            f'x1="{start}" y1="0" x2="204" y2="0" stroke="{color}" '
            f'stroke-width="{width}" transform="translate(256 256) rotate({angle:.6f})"/>'
        )
    lines.extend(['  </g>', f'  <g id="days" fill="{ink}" data-count="{day}" '
                  f'transform="translate(256 256) rotate({commits % 360})">'])
    for i in range(day):
        ring, slot = divmod(i, 24)
        count = min(24, day - ring * 24)
        radius = inner_radius - ring * radial_step
        angle = -90 + 360 * slot / count
        lines.append(f'    <circle id="day-{i + 1}" class="day" cx="{radius:.6f}" '
                     f'cy="0" r="{dot_radius:.6f}" transform="rotate({angle:.6f})"/>')
    lines.extend(['  </g>', '</svg>', ''])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('day', 'loops', 'loops-target', 'commits'):
        parser.add_argument('--' + name, type=int, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mono', action='store_true', help='use ink for closed ticks too')
    parser.add_argument('--variant', choices=PALETTES, default='seal')
    args = parser.parse_args()
    try:
        content = svg(args.day, args.loops, args.loops_target, args.commits,
                      args.mono, args.variant)
    except ValueError as error:
        parser.error(str(error))
    args.out.write_bytes(content.encode('utf-8'))


if __name__ == '__main__':
    main()
