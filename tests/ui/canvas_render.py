import io

import click


class CanvasTranslator:
    """Translates a canvas object into a printable string."""

    def __init__(self, canvas, palette=None):
        """currently only support foreground colors, so palette is
        a dictionary of attributes and foreground colors"""
        self._canvas = canvas
        self._palette = {}
        if palette:
            for key, color in palette.items():
                self.add_color(key, color)

    def add_color(self, key, color):
        if color.startswith('#'):  # RGB colour
            r = color[1:3]
            g = color[3:5]
            b = color[5:8]
            rgb = int(r, 16), int(g, 16), int(b, 16)
            value = True, '\33[38;2;{!s};{!s};{!s}m'.format(*rgb)
        else:
            color = color.split(' ')[-1]
            if color == 'gray':
                color = 'white'  # click will insist on US-english
            value = False, color

        self._palette[key] = value  # (is_ansi, color)

    def transform(self):
        self.output = io.StringIO()
        for row in self._canvas.content():
            # self.spaces = 0
            for col in row[:-1]:
                self._process_char(*col)
            # the last column has all the trailing whitespace, which deforms
            # everything if the terminal is resized:
            col = row[-1]
            self._process_char(col[0], col[1], col[2].rstrip())

            self.output.write('\n')

        return self.output.getvalue()

    def _process_char(self, fmt, _, b):
        text = b.decode()
        if not fmt:
            self.output.write(text)
        else:
            fmt = self._palette[fmt]
            if fmt[0]:
                self.output.write(f'{fmt[1]}{click.style(text)}')
            else:
                self.output.write(click.style(text, fg=fmt[1]))
