#! /usr/bin/env pypy

""" Image to emoji converter - Jackson Sommerich 2017
    This program is intended to be using pypy or pypy3, cpython is far too slow.
"""

import os
import argparse
import itertools

from PIL import Image
from tqdm import tqdm

class Emoji(object):
    def __init__(self, image):
        self.name = image
        self.image = self._process_emoji(image)
        self.colour = self._set_colour()

    def _process_emoji(self, image):
        im = Image.open(image)
        if im.size != (20, 20):
            im.thumbnail((20, 20))
        if args.transparency:
            return im.convert("RGBA")
        alpha = im.convert('RGBA').split()[-1]
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.paste(im, mask=alpha)
        return bg.convert("RGB")

    def _set_colour(self):
        image = self.image.copy()
        image = image.resize((1, 1), resample=Image.LANCZOS)
        colour = image.getpixel((0, 0))
        image.close()
        return colour

    def get_distance(self, pixel):
        return ((self.colour[0] - pixel[0]) ** 2 +
                (self.colour[1] - pixel[1]) ** 2 +
                (self.colour[2] - pixel[2]) ** 2)

    def get_emoji(self):
        return self.image


class Picture(object):
    def __init__(self, image, max_size, keeptransparency=False):
        self.image = self._process_image(image, max_size, keeptransparency)
        self.width, self.height = self.image.size
        self.canvas_size = (self.image.width * 20, self.image.height * 20)
        if keeptransparency:
            self.canvas = Image.new("RGBA", self.canvas_size, color=(255, 255, 255, 0))
        else:
            self.canvas = Image.new("RGB", self.canvas_size, color=(255, 255, 255))

    def _process_image(self, image, max_size, keeptransparency):
        im = Image.open(image)
        # Remove PNG transparency: https://stackoverflow.com/a/35859141
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            alpha = im.convert("RGBA").split()[-1]
            bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
            bg.paste(im, mask=alpha)
            im = bg
        # Resize the input image keeping the aspect ratio correct
        im.thumbnail((max_size, max_size), resample=Image.LANCZOS)
        if keeptransparency:
            return im
        return im.convert("RGB")

    def paste_emoji(self, pos, emoji):
        self.canvas.paste(emoji.get_emoji(), box=(pos[0] * 20, pos[1] * 20))

    def get_pixel(self, pos):
        return self.image.getpixel(pos)

    def save_canvas(self, location, format="png"):
        # Save the image, type is determined by extension, or in case of no
        # extension is saved as png
        try:
            self.canvas.save(location)
        except ValueError:
            self.canvas.save(location, format=format)

if __name__ == "__main__":
    # Arguments collection and processing
    args = argparse.ArgumentParser()

    args.add_argument("image",
                      help="Input image to process.")

    args.add_argument("--transparency", "-t",
                      action="store_true",
                      help="Keep the transparency layer in the input image.")

    args.add_argument("--emoji", "-e",
                      help="Directory to retrieve emoji from.",
                      default="emoji")

    args.add_argument("--size", "-s",
                      type=int,
                      help="Maximum resolution for longest edge.",
                      default=512)

    args.add_argument("--output", "-o",
                      help="Output image name.")

    args = args.parse_args()

    # Create an emoji object for each png file in the emoji directory
    emoji = [Emoji(os.path.join(args.emoji, x)) for x in
        filter(lambda x: "png" in x, os.listdir(args.emoji))]

    image = Picture(args.image, args.size, keeptransparency=args.transparency)

    print("Creating {}x{} image from {}x{} image and {} emoji:".format(
        image.width * 20, image.height * 20, image.width, image.height,
        len(emoji)))

    previous_chars = dict()

    for y in tqdm(range(image.height), unit="rows"):
        for x in range(image.width):
            colour = image.get_pixel((x, y))
            if args.transparency and colour[-1] >= 240 and\
                colour[0] >= 240 and colour[1] >= 240 and colour[2] >= 240:
                continue
            elif not args.transparency and colour == (255, 255, 255):
                continue
            try:
                out_emoji = previous_chars[colour]
            except KeyError:
                out_emoji = min(emoji, key=lambda x: x.get_distance(colour))
                previous_chars[colour] = out_emoji
            image.paste_emoji((x, y), out_emoji)

    output_path = args.output

    # Create an output name if none set, if file exists add a number to the end
    if output_path is None:
        input_path_no_ext = os.path.splitext(args.image)[0]
        output_path = "{} - Output.png".format(input_path_no_ext)
        for x in itertools.count(start=1):
            if not os.path.exists(output_path):
                break
            output_path = "{} - Output ({}).png".format(input_path_no_ext, x)

    print("Saving image to \"{}\"...".format(output_path))
    image.save_canvas(output_path)
    print("Done")
