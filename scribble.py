import random
import itertools
import math

from PIL import Image, ImageFilter, ImageDraw


# Image processing code heavily adapted from:
# https://github.com/Scott-Cooper/Drawbot_image_to_gcode_v2


class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __repr__(self):
        return '(%d, %d)' % (self.x, self.y)

    def constrain(self, x=None, y=None):
        if x:
            self.x = max(min(self.x, x[1]), x[0])
        if y:
            self.y = max(min(self.y, y[1]), y[0])

    def coords(self):
        return (self.x, self.y)


def bresenham(start, finish):
    dx = abs(finish.x - start.x)
    dy = abs(finish.y - start.y)
    sx = 1 if start.x < finish.x else -1
    sy = 1 if start.y < finish.y else -1
    err = dx - dy
    
    loc = Point(start.x, start.y)
    yield loc

    while loc.x != finish.x and loc.y != finish.y:
        if (err * 2) > (-1 * dy):
            err -= dy
            loc.x += sx
        if (err * 2) < dx:
            err += dx
            loc.y += sy
        yield loc


class Source:
    def __init__(self, img):
        self.original = Image.open(img)
        self.image = self.original.copy().convert('L')
        self.px = self.image.load()

    def darkest_area(self, down_sample=10):
        condensed = self.image.resize((self.image.width // down_sample, self.image.height // down_sample))
        cpx = condensed.load()

        darkest_val = None
        darkest_loc = None
        for x, y in itertools.product(range(condensed.width), range(condensed.height)):
            if not darkest_val or cpx[x, y] < darkest_val:
                darkest_val = cpx[x, y] + random.random()
                darkest_loc = Point(x, y)

        return Point(
            int(darkest_loc.x * (down_sample + random.random())),
            int(darkest_loc.y * (down_sample + random.random()))
        )

    angle_methods = {
        'spitfire': lambda: random.randint(-72, -52),
    }

    def darkest_neighbor(self, start, line_length=20, tests=13, angle_method=angle_methods['spitfire']):
        start_angle = angle_method()
        start.constrain((0, self.image.width - 1), (0, self.image.height - 1))

        darkest_value = 256
        darkest_point = None

        for step in range(tests):
            angle = math.radians(start_angle + 360 / tests * step)
            finish = Point(
                start.x + int(math.cos(angle) * line_length),
                start.y + int(math.sin(angle) * line_length)
            )
            finish.constrain((0, self.image.width - 1), (0, self.image.height - 1))

            bright_sum, bright_count = 0, 0
            for pt in bresenham(start, finish):
                bright_count += 1
                bright_sum += self.px[pt.x, pt.y]
                if (bright_sum / bright_count) < darkest_value:
                    darkest_value = bright_sum / bright_count
                    darkest_point = Point(pt.x, pt.y)

        return darkest_point

    def average_brightness(self):
        bright_total = 0
        for x, y in itertools.product(range(self.image.width), range(self.image.height)):
            bright_total += self.px[x, y]
        return bright_total / (self.image.width * self.image.height)

    def lighten(self, start, finish, amount=10):
        for pt in bresenham(start, finish):
            self.image.putpixel(pt.coords(), (min(255, self.px[pt.x, pt.y] + amount),))


if __name__ == '__main__':
    src = Source('baby.jpg')
    visual = Image.new('L', (src.image.width, src.image.height), 255)
    model = ImageDraw.Draw(visual)

    squiggle_length = 500

    squiggles = 0
    while src.average_brightness() < 240:
        squiggles += 1
        darkest_start = src.darkest_area()
        for _ in range(squiggle_length):
            darkest_next = src.darkest_neighbor(darkest_start)
            src.lighten(darkest_start, darkest_next)
            model.line([darkest_start.coords(), darkest_next.coords()], 0)
            darkest_start = darkest_next
        print('squiggles = %d, brightness =' % squiggles, src.average_brightness())
    visual.show()
