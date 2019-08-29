import random
import itertools
import math
import sys

from PIL import Image, ImageFilter, ImageDraw, ImageStat


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

    def coords(self, scale=1.0):
        return (int(self.x * scale), int(self.y * scale))


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

    def scale_width(self, width):
        self.image = self.image.resize((width, self.image.height * width // self.image.width))

    def darkest_area(self, down_sample=10):
        condensed = self.image.resize((self.image.width // down_sample, self.image.height // down_sample))

        darkest_val = None
        darkest_loc = None
        for x, y in itertools.product(range(condensed.width), range(condensed.height)):
            if not darkest_val or condensed.getpixel((x, y)) < darkest_val:
                darkest_val = condensed.getpixel((x, y)) + random.random()
                darkest_loc = Point(x, y)

        return Point(
            int(darkest_loc.x * (down_sample + random.random())),
            int(darkest_loc.y * (down_sample + random.random()))
        )

    angle_methods = {
        'spitfire': lambda: random.randint(-72, -52),
    }

    def darkest_neighbor(self, start, line_length=10, tests=10, angle_method=angle_methods['spitfire']):
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
                bright_sum += self.image.getpixel(pt.coords())
                if (bright_sum / bright_count) < darkest_value:
                    darkest_value = bright_sum / bright_count
                    darkest_point = Point(pt.x, pt.y)

        return darkest_point

    def average_brightness(self):
        return ImageStat.Stat(self.image).mean[0]

    def lighten(self, start, finish, amount=120):
        for pt in bresenham(start, finish):
            self.image.putpixel(pt.coords(), (min(255, self.image.getpixel(pt.coords()) + amount),))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: %s [image]' % sys.argv[0])
        sys.exit(1)

    src = Source(sys.argv[1])
    src.scale_width(400)

    visual_scale = 4.0

    visual = Image.new('L', (int(src.image.width * visual_scale), int(src.image.height * visual_scale)), 255)
    model = ImageDraw.Draw(visual)

    squiggle_length = 500
    brightness_threshold = 240

    squiggles = 0
    while src.average_brightness() < brightness_threshold:
        squiggles += 1
        darkest_start = src.darkest_area()
        for s in range(squiggle_length):
            darkest_next = src.darkest_neighbor(darkest_start)
            src.lighten(darkest_start, darkest_next)
            model.line([darkest_start.coords(scale=visual_scale), darkest_next.coords(scale=visual_scale)], 0)
            darkest_start = darkest_next

    visual.show()
