#!/usr/bin/env python

# This is a really simple implementation of error level analyzes as described in
# http://blackhat.com/presentations/bh-dc-08/Krawetz/Whitepaper/bh-dc-08-krawetz-WP.pdf
# You shouldn't actually use it, or at least read the paper carefully
# and implement more of the techniques before drawing any conclusions.
# based on: https://gist.github.com/ewencp/3356622

import os.path
from pathlib import Path
from PIL import Image, ImageChops, ImageEnhance
import click
from exif import Image as exif_Image

try:
    from StringIO import StringIO
except ImportError:
    from io import BytesIO as StringIO


@click.command()
@click.option("--in", "-i", "in_files", required=True,
              help="Path to jpg file or folder of jpgs to be processed.",
              type=click.Path(exists=True, dir_okay=True, readable=True),
              )
@click.option("--out-dir", "-o", default="./",
              type=click.Path(dir_okay=True, file_okay=False),
              help="Path to folder to store the results.")
@click.option("--min-quality", "-min", default=5,
              type=click.IntRange(1, 100),
              help="minimal quality for pictures")
@click.option("--max-quality", "-max", default="101",
              type=click.IntRange(3, 101),
              help="maximal quality for pictures")
@click.option("--quality-steps", "-steps", "steps", default=5,
              type=click.IntRange(1, 100),
              help="quality steps for pictures")
@click.option("--t", "-thumb_diff", "thumb_diff", is_flag=True,
              help="compares thumbnail with original")
def cli(in_files, out_dir, min_quality, max_quality, steps, thumb_diff):
    if os.path.isdir(in_files):
        in_files_files = [file for file in os.listdir(in_files) if file.endswith('.jpg')]
        for file in in_files_files:
            subfolder = os.path.join(out_dir, Path(file).stem)
            print(subfolder)
            process_file(os.path.join(in_files, file), subfolder, max_quality, min_quality, steps, thumb_diff)
    else:
        process_file(in_files, out_dir, max_quality, min_quality, steps, thumb_diff)


def process_file(filename, out_dir, max_quality, min_quality, steps, thumb_diff):
    for q_step in range(min_quality, max_quality, steps):
        os.makedirs(out_dir, exist_ok=True)
        resaved = os.path.join(out_dir, Path(filename).stem + f"_q_{q_step}_resaved.jpg")
        error_analyze = os.path.join(out_dir, Path(filename).stem + f"_q_{q_step}_error_analyze.png")
        im = Image.open(filename)

        im.save(resaved, 'JPEG', quality=q_step)
        resavedf = Image.open(resaved)

        error_analyze_im = ImageChops.difference(im, resavedf)
        extrema = error_analyze_im.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        scale = 255.0 / max_diff

        error_analyze_im = ImageEnhance.Brightness(error_analyze_im).enhance(scale)
        error_analyze_im.save(error_analyze)
        os.remove(resaved)
        if thumb_diff:
            compare_thumbnail(filename, out_dir)


def compare_thumbnail(filename, out_dir):
    with open(filename, 'rb') as image_file:
        image_bytes = image_file.read()
        my_image = exif_Image(image_bytes)
        try:
            thumb = my_image.get_thumbnail()
            output = StringIO()
            output.write(thumb)
            output.seek(0)
            thumbnail = Image.open(output)
            original = Image.open(filename)
            width, height = thumbnail.size
            try:
                original = original.resize([width, height], Image.ANTIALIAS)
            except IOError as e:
                raise Exception("Comparer error reading image: {0}".format(e))
            diff = ImageChops.difference(original, thumbnail)
            resaved = os.path.join(out_dir, Path(filename).stem + f"_thumb_diff.jpg")
            diff.save(resaved, 'JPEG', quality=95)
        except RuntimeError as e:
            print("no thumbnail in Image")


if __name__ == "__main__":
    cli()
