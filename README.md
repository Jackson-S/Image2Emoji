# 🖼➡️😊 (Image2Emoji)
### What is this?
This script takes in an image file in any format Pillow supports, and outputs
the same file but made up of emoji.

![Imagine an image, but made of emoji, then insert it in this spot and be amazed.](sample.png "Emoji Sample")

### Motivation
I needed more emoji in my life. One can never have enough emoji 👌

### Where do I get emoji from?
If you're on MacOS then the program will automatically extract the included
emoji from the system. Otherwise you can use the [emojione](https://www.emojione.com/developers/download) emoji set.

### Requirements
 - Python 2/3
 - Pillow (recommended) or PIL
 - tqdm

### Usage
The program has been tested on MacOS, Windows and Ubuntu.
If running on an OS other than MacOS then place emoji into a folder called
"emoji", or specify a folder using the -e option.

When installing pillow ensure that you have PNG support (requires zLib).

I recommend you run this with pypy, cpython is a bit slow.
