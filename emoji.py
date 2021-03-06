""" Image to emoji converter - Jackson Sommerich, 2017
"""

import os
import re
import sys
import struct
import argparse
import itertools

from PIL import Image
from tqdm import tqdm

class EmojiExtractor(object):
    """Finds PNG images in Apple Color Emoji.tt(c|f) and extracts them"""
    def __init__(self, location=None):
        self.font = self._read_in_font(location)

    def _read_in_font(self, location=None):
        """ Private method to read font file as binary data. """
        # If a user font location is specified then read in that font
        if location is not None:
            if not os.path.exists(location):
                raise FileNotFoundError("{} not found!".format(location))

            with open(location, "rb") as font_file:
                return font_file.read()

        # Get the path to the font file, OSX 10.12 changed to .ttc from .ttf
        font_path = "/System/Library/Fonts/"
        font_name = ("Apple Color Emoji.ttf", "Apple Color Emoji.ttc")
        for name in font_name:
            if os.path.exists(os.path.join(font_path, name)):
                with open(os.path.join(font_path, name), "rb") as font_file:
                    return font_file.read()

        raise FileNotFoundError("Could not find Apple Color Emoji font!")

    def extract_emoji(self, size):
        """Extracts emoji into ./emoji, only works for OSX"""
        # Create the output folder
        if not os.path.exists("emoji"):
            os.mkdir("emoji")

        counter = 0

        # Iterate through locations of all PNG headers files, up to IEND id.
        pattern = re.compile(b"\x89PNG\r\n\x1a\n.*?IEND", flags=re.DOTALL)
        for item in re.finditer(pattern, self.font):
            start = item.start()
            end = item.end()
            # Add the size of the IEND block, minus the size accounted for
            end += struct.unpack(">I", self.font[end-8:end-4])[0] + 4

            # Check for the correct horzontal size
            if size == struct.unpack(">I", self.font[start+16:start+20])[0]:
                file_path = os.path.join("emoji", "{}.png".format(counter))
                counter += 1
                with open(file_path, "wb") as out_file:
                    out_file.write(self.font[start:end])


class Emoji(object):
    """ A single emoji object, contains emoji image, and functions for
        determining colour of emoji
    """
    def __init__(self, image, size, transp):
        self.image = self._process_emoji(image, size, transp)
        self.colour = self._set_colour(image)

    def _process_emoji(self, image_path, size, transp):
        image = Image.open(image_path)
        if image.size != (size, size):
            try:
                filter_algorithm = Image.LANCZOS
            except AttributeError:
                filter_algorithm = Image.BICUBIC
            image = image.resize((size, size), resample=filter_algorithm)
        alpha = image.convert('RGBA').split()[-1]
        new_image = Image.new("RGBA", image.size, (255, 255, 255, 0))
        new_image.paste(image, mask=alpha)
        if transp:
            return new_image
        return new_image.convert("RGB")

    def _set_colour(self, image_path):
        image = Image.open(image_path)
        background = Image.new("RGBA", image.size, (255, 255, 255, 255))
        background.paste(image, mask=image.convert("RGBA").split()[-1])
        try:
            background = background.resize((1, 1), resample=Image.LANCZOS)
        except AttributeError:
            background = background.resize((1, 1), resample=Image.BICUBIC)
        return background.getpixel((0, 0))

    def get_distance(self, pixel):
        return (abs(self.colour[0] - pixel[0]) +
                abs(self.colour[1] - pixel[1]) +
                abs(self.colour[2] - pixel[2]))

    def get_emoji(self):
        return self.image


class Picture(object):
    def __init__(self, image, max_size, emoji_size, transparency):
        self.image = self._process_image(image, max_size)
        self.width, self.height = self.image.size
        self.canvas_size = (self.width * emoji_size, self.height * emoji_size)
        col_space = "RGBA" if transparency else "RGB"
        background = (255, 255, 255, 0) if transparency else (255, 255, 255)
        self.canvas = Image.new(col_space, self.canvas_size, color=background)

    def _process_image(self, image_path, max_size):
        image = Image.open(image_path)
        # Remove PNG transparency: https://stackoverflow.com/a/35859141
        if image.mode in ("RGBA", "LA") or (image.mode is "P" and "tran" in image.info):
            alpha = image.convert("RGBA").split()[-1]
            new_image = Image.new("RGBA", image.size, (255, 255, 255, 255))
            new_image.paste(image, mask=alpha)
            image = new_image
        # Resize the input image keeping the aspect ratio correct
        try:
            filter_algorithm = Image.LANCZOS
        except AttributeError:
            filter_algorithm = Image.BICUBIC
        image.thumbnail((max_size, max_size), resample=filter_algorithm)
        return image

    def paste_emoji(self, pos, emoji, emoji_size):
        self.canvas.paste(emoji.get_emoji(),
                          box=(pos[0] * emoji_size, pos[1] * emoji_size))

    def get_pixel(self, pos):
        return self.image.getpixel(pos)

    def save_canvas(self, location, image_format="png"):
        # Save the image, type is determined by extension, or in case of no
        # extension is saved as png
        try:
            self.canvas.save(location)
        except ValueError:
            self.canvas.save(location, format=image_format)

def main():
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

    # If no emoji directory exists and none is specified
    if args.emoji is None:
        if not os.path.exists("emoji") or not os.listdir("emoji"):
            print("Attempting to extract emoji from emoji font...")
            try:
                EmojiExtractor().extract_emoji(emoji_size)
            except FileNotFoundError:
                print("Failed to auto-extract emoji (only works on MacOS). "
                      "Specify a directory with pre-extracted emoji using -e to "
                      "continue.")
                sys.exit(1)

    # Make a directory listing of each png in the emoji directory
    print("Processing emoji...")
    if args.emoji is not None:
        path_list = filter(lambda name: "png" in name, os.listdir(args.emoji))
        path_list = map(lambda name: os.path.join(args.emoji, name), path_list)
    else:
        path_list = filter(lambda name: "png" in name, os.listdir("emoji"))
        path_list = map(lambda name: os.path.join("emoji", name), path_list)

    # Create emoji objects for each file in the listing
    emoji = [Emoji(path, emoji_size, args.transparency) for path in path_list]

    image = Picture(args.image, args.size, emoji_size, args.transparency)

    print("Creating {}x{} image from {}x{} image and {} emoji:".format(
        image.width * emoji_size, image.height * emoji_size,
        image.width, image.height, len(emoji)))

    previous_colours = dict()
    colour = None

    for y in tqdm(range(image.height), unit="rows"):
        for x in range(image.width):
            colour = image.get_pixel((x, y))
            # If a colour is very close to white then skip it, avoids weird
            # edges when converting images with transparency.
            if min(colour) >= 252:
                continue
            try:
                out_emoji = previous_colours[colour]
            except KeyError:
                out_emoji = min(emoji, key=lambda x: x.get_distance(colour))
                previous_colours[colour] = out_emoji
            image.paste_emoji((x, y), out_emoji, emoji_size)

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

if __name__ == "__main__":
    main()
