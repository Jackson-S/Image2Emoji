#! /usr/bin/env pypy

""" Image to emoji converter - Jackson Sommerich 2017
    This program is intended to be using pypy or pypy3, cpython is far too slow.
"""

import os
import re
import sys
import struct
import platform
import argparse
import itertools

from PIL import Image
from tqdm import tqdm

def extract_emoji(emoji_size):
    """ Extracts emoji on OSX into an emoji folder. Return True if successful"""

    # Get the path to the font file, OSX 10.12 changed to .ttc from .ttf
    font_path = "/System/Library/Fonts/Apple Color Emoji"
    if os.uname()[0] == "Darwin":
        if int(platform.mac_ver()[0].split(".")[1]) >= 12:
            font_path += ".ttc"
        else:
            font_path += ".ttf"

    if font_path is None or not os.path.exists(font_path):
        return False

    with open(font_path, "rb") as font_file:
        font = font_file.read()

    # Fetch locations of all PNG headers in font file
    header_location = re.finditer(b'\x89PNG\r\n\x1a\n', font)
    writing = False
    emoji_array = list()

    while True:
        if not writing:
            # Go to next occurence of png header
            try:
                index = next(header_location).start()
            except StopIteration:
                break

            # Calculate the chunk size, but getting the data size and adding
            # the metadata size to it (20 for IHDR and 12 for other chunks).
            # Uses struct.unpack to convert from bytes to unsigned int (>I).
            chunk_size = struct.unpack(">I", font[index+8:index+12])[0] + 20

            # Ensure the correct size emoji is selected by reading the width
            if emoji_size != struct.unpack(">I", font[index+16:index+20])[0]:
                continue

            writing = True
            emoji_array.append(bytearray(font[index:index+chunk_size]))

            index += chunk_size

        # Check for the IEND (Final) block
        elif writing and font[index+4:index+8] == b"IEND":
            chunk_size = struct.unpack(">I", font[index:index+4])[0] + 12
            emoji_array[-1].extend(font[index:index+chunk_size])
            emoji_array[-1] = bytes(emoji_array[-1])
            writing = False

            index += chunk_size

        # For all blocks between IHDR and IEND
        elif writing:
            chunk_size = struct.unpack(">I", font[index:index+4])[0] + 12
            emoji_array[-1].extend(font[index:index+chunk_size])

            index += chunk_size

    if len(emoji_array) != 0:
        # Output all emoji into a folder
        if not os.path.exists("emoji"):
            os.mkdir("emoji")
        for index, emoji in enumerate(emoji_array):
            with open("emoji/{}.png".format(index), "wb") as out_file:
                out_file.write(emoji)
        return True

    else:
        return False


class Emoji(object):
    def __init__(self, image, size, transp):
        self.name = image
        self.image = self._process_emoji(size, transp)
        self.colour = self._set_colour()

    def _process_emoji(self, size, transp):
        im = Image.open(self.name)
        if im.size != (size, size):
            try:
                filter_algorithm = Image.LANCZOS
            except AttributeError:
                filter_algorithm = Image.BICUBIC
            im = im.resize((size, size), resample=filter_algorithm)
        alpha = im.convert('RGBA').split()[-1]
        bg = Image.new("RGBA", im.size, (255, 255, 255, 0))
        bg.paste(im, mask=alpha)
        if transp:
            return bg
        return bg.convert("RGB")

    def _set_colour(self):
        image = Image.open(self.name)
        background = Image.new("RGBA", image.size, (255, 255, 255, 255))
        background.paste(image, mask=image.convert('RGBA').split()[-1])
        try:
            filter_algorithm = Image.LANCZOS
        except AttributeError:
            filter_algorithm = Image.BICUBIC
        background = background.resize((1, 1), resample=filter_algorithm)
        colour = background.getpixel((0, 0))
        background.close()
        image.close()
        return colour

    def get_distance(self, pixel):
        return (abs(self.colour[0] - pixel[0]) +
                abs(self.colour[1] - pixel[1]) +
                abs(self.colour[2] - pixel[2]))

    def get_emoji(self):
        return self.image


class Picture(object):
    def __init__(self, image, max_size, emoji_size, transp):
        self.image = self._process_image(image, max_size, transp)
        self.width, self.height = self.image.size
        self.canvas_size = (self.image.width * emoji_size,
                            self.image.height * emoji_size)
        col_space = "RGBA" if transp else "RGB"
        background = (255, 255, 255, 0) if transp else (255, 255, 255)
        self.canvas = Image.new(col_space, self.canvas_size, color=background)

    def _process_image(self, image, max_size, transp):
        im = Image.open(image)
        # Remove PNG transparency: https://stackoverflow.com/a/35859141
        if im.mode is "RGBA" or "LA" or (im.mode is "P" and "trans" in im.info):
            alpha = im.convert("RGBA").split()[-1]
            bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
            bg.paste(im, mask=alpha)
            im = bg
        # Resize the input image keeping the aspect ratio correct
        try:
            filter_algorithm = Image.LANCZOS
        except AttributeError:
            filter_algorithm = Image.BICUBIC
        im.thumbnail((max_size, max_size), resample=filter_algorithm)
        return im

    def paste_emoji(self, pos, emoji):
        self.canvas.paste(emoji.get_emoji(),
                          box=(pos[0] * emoji_size, pos[1] * emoji_size))

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
                      default=None)

    args.add_argument("--emoji-size", "-d",
                      type=int,
                      help="The longest edge length of emoji you are using.",
                      default=20)

    args.add_argument("--size", "-s",
                      type=int,
                      help="Maximum resolution for longest edge.",
                      default=512)

    args.add_argument("--output", "-o",
                      help="Output image name.")

    args = args.parse_args()
    emoji_size = args.emoji_size
    transp = args.transparency

    if args.emoji is None and not os.path.exists("emoji"):
        print("Attempting to extract emoji from emoji font...")
        if extract_emoji(emoji_size) is False:
            print("Failed to extract emoji (only works on MacOS). "
                  "Specify a directory with pre-extracted emoji using -e to "
                  "continue.")
            sys.exit(1)

        print("Processing emoji...")
        emoji = [Emoji(os.path.join("emoji", x), emoji_size, transp) for x in
                 filter(lambda x: "png" in x, os.listdir("emoji"))]
    elif args.emoji is not None:
        # Create an emoji object for each png file in the emoji directory
        emoji = [Emoji(os.path.join(args.emoji, x), emoji_size, transp) for x in
                 filter(lambda x: "png" in x, os.listdir(args.emoji))]

    else:
        emoji = [Emoji(os.path.join("emoji", x), emoji_size, transp) for x in
                 filter(lambda x: "png" in x, os.listdir("emoji"))]

    image = Picture(args.image, args.size, emoji_size, transp)

    print("Creating {}x{} image from {}x{} image and {} emoji:".format(
        image.width * emoji_size, image.height * emoji_size,
        image.width, image.height, len(emoji)))

    previous_chars = dict()

    for y in tqdm(range(image.height), unit="rows"):
        for x in range(image.width):
            colour = image.get_pixel((x, y))
            # If a colour is very close to white then skip it, avoids weird
            # edges when converting images with transparency.
            if min(colour) >= 252:
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
