import argparse
import os
import math
import pathlib

try:
    from PIL import Image
    import numpy as np
except ModuleNotFoundError:
    print("Installing deps, please wait...")
    os.system("pip install -r requirements.txt")
    try:
        import numpy as np
        from PIL import Image
    except ModuleNotFoundError:
        print("Pillow not installed. Check your internet connection ant try again, or install pillow manual")


def get_new_val(old_val, nc):
    return np.round(old_val * (nc - 1)) / (nc - 1)


def fs_dither(img, nc):
    arr = np.array(img, dtype=float) / 255
    for ir in range(img.height):
        for ic in range(img.width):
            # NB need to copy here for RGB arrays otherwise err will be (0,0,0)!
            old_val = arr[ir, ic].copy()
            new_val = get_new_val(old_val, nc)
            arr[ir, ic] = new_val
            err = old_val - new_val
            # In this simple example, we will just ignore the border pixels.
            if ic < img.width - 1:
                arr[ir, ic + 1] += err * 7 / 16
            if ir < img.height - 1:
                if ic > 0:
                    arr[ir + 1, ic - 1] += err * 3 / 16
                arr[ir + 1, ic] += err * 5 / 16
                if ic < img.height - 1:
                    arr[ir + 1, ic + 1] += err / 16

    carr = np.array(arr / np.max(arr, axis=(0, 1)) * 255, dtype=np.uint8)
    return Image.fromarray(carr)


def main():
    parser = argparse.ArgumentParser(prog="img2cpp", description="Image to OLED-style bitmap converter",
                                     epilog="Created by KapitanN3mo")
    parser.add_argument("-i", "--input", help="Input image file", required=True)
    parser.add_argument("-o", "--output", help="Output file name")
    parser.add_argument("-s", "--size", help="Vertical output bitmap size (height)")
    parser.add_argument("-n", "--bmname", help="Bitmap array name")
    args = parser.parse_args()
    print("Opening image...",end="")
    try:
        img = Image.open(args.input)
        print("  OK")
    except FileNotFoundError:
        print(f"File {args.input} not found")
        return

    width, height = img.size
    try:
        new_height = height if args.size is None else int(args.size)
    except (ValueError, TypeError):
        print("Incorrect width!")
        return

    print("Converting to grayscale...",end="")
    img = img.convert("L")
    print("  OK")
    new_width = int(width * new_height / height)
    img = img.resize((new_width, new_height), Image.LANCZOS)
    print("Applying Floyd-Steinberg dithering filter...",end="")
    img = fs_dither(img, 2)
    print("  OK")
    print("Creating bitmap array...",end="")
    out = np.zeros((math.ceil(img.height / 8), width), dtype=np.uint8)
    for page in range(math.ceil(img.height / 8)):
        for x in range(img.width):
            for y in range(0, 8):
                val = 0 if img.getpixel((x, (page * 8) + y)) == 0 else 1
                out[page][x] |= (val << y)
    print("  OK")
    print("Creating header file...",end="")
    filename = args.output if args.output is not None else args.input[0:args.input.find(".")]
    bitmap_name = args.bmname if args.bmname is not None else filename
    with open(filename + ".h", 'w') as file:
        file.write(f"extern uint8_t {bitmap_name}[{math.ceil(img.height / 8)}][{img.width}];")
    print("  OK")
    print("Creating C file...",end="")
    with open(filename + ".c", "w") as file:
        file.write(f"#include \"{filename}.h\"\n")
        file.write(f"\nuint8_t {bitmap_name}[{math.ceil(img.height / 8)}][{img.width}];")
        file.write("\nvoid initImage() {\n")
        for x in range(math.ceil(img.height / 8)):
            for y in range(img.width):
                file.write(f"\t\t{bitmap_name}[{x}][{y}] = {out[x][y]};\n")
        file.write("}")
    print("  OK")
    print(
        f"Complete!\nImage size: {img.width}x{img.height}\nMemory usage: {img.width * math.ceil(img.height / 8)} bytes")


if __name__ == '__main__':
    main()
