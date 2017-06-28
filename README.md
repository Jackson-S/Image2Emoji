# 🖼➡️😊 (Image2Emoji)
### What is this?
This script takes in an image file in any format Pillow supports, and outputs the same file but made up of emoji.

![Imagine an image, but made of emoji, then insert it in this spot and be amazed.](sample.png "Emoji Sample")

### Motivation
I needed more emoji in my life. One can never have enough emoji 👌

### Where do I get emoji from?
You can use [this](https://github.com/tmm1/emoji-extractor) with the 20x20 emoji or if you lack a mac you can retrieve emoji from you can use the 32x32 png [emojione](https://www.emojione.com/developers/download) emoji set.

### Usage
The program has been tested on MacOS, Windows and Ubuntu.

Once you have emoji place them into a folder called emoji (or specify the path with -e when running the script), then install the requirements with pip and run it in pypy or pypy3.
If you have trouble installing pillow on pypy2/3 ensure libjpeg is installed and up to date on your computer.
You _can_ use cpython but you will be waiting a **long** time for it to process.
