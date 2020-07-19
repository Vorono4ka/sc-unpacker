import json
import lzma
import os
import sys

from PIL import Image, ImageDraw

from utils.reader import Reader


def _(*args):
    print(f'[SC Tool] ', end='')
    for arg in args:
        print(arg, end=' ')
    print()


def _i(text: str):
    return input(f'[SC Tool] {text}: ')


def _e(*args):
    print('[Error] ', end='')
    for arg in args:
        print(arg, end=' ')
    print()
    input('Press Enter to exit: ')
    sys.exit()


class SC:
    def __init__(self, filename: str):
        self.base_name = filename.split('.sc')[0]
        self.info_name = self.base_name + '.sc.parsed.json'

        self.info = json.load(open(f'parsed/{self.info_name}'))

        self.shapes = self.info['shapes']
        self.animations = self.info['animations']
        self.textures_info = self.info['textures']
        self.text_fields = self.info['text_fields']
        self.matrices = self.info['matrices']
        self.color_transformations = self.info['color_transformations']
        self.exports = self.info['exports']['names']

        self.textures = []
        for file in os.listdir(f'png/{self.base_name}_tex'):
            self.textures.append(Image.open(f'png/{self.base_name}_tex/{file}'))
        self.filename = filename

    def generate_shapes(self):
        export_folder = f'sprites/{self.filename.split(".sc")[0]}/'
        if not os.path.exists(export_folder):
            os.mkdir(export_folder)

        for x in range(len(self.shapes)):
            for y in range(len(self.shapes[x]['regions'])):
                shape_name = self.shapes[x]['name'] if 'name' in self.shapes[x] else None
                region = self.shapes[x]['regions'][y]

                polygon = [region['sheet_points'][z] for z in range(len(region['sheet_points']))]

                polygon = [tuple(point) for point in polygon]
                print(polygon)

                size = (
                    self.textures_info[region['sheet_id']]['size'][0],
                    self.textures_info[region['sheet_id']]['size'][1]
                )

                imMask = Image.new('L', size, 0)
                ImageDraw.Draw(imMask).polygon(polygon, fill=255)
                bbox = imMask.getbbox()
                if not bbox:
                    continue

                region_size = (bbox[2] - bbox[0], bbox[3] - bbox[1])
                tmpRegion = Image.new('RGBA', region_size, None)
                tmpRegion.paste(self.textures[region['sheet_id']].crop(bbox), None, imMask.crop(bbox))
                if region['mirroring']:
                    tmpRegion = tmpRegion.transform(region_size, Image.EXTENT, (region_size[0], 0, 0, region_size[1]))

                if shape_name is not None:
                    export_path = f'{export_folder}/{shape_name}_{x}_{y}.png'
                else:
                    export_path = f'{export_folder}/{x}_{y}.png'
                tmpRegion.rotate(region['rotation'], expand=True).save(export_path)


if __name__ == '__main__':
    if not os.path.exists('decompressed'):
        os.mkdir('decompressed')
    if not os.path.exists('compressed'):
        os.mkdir('compressed')

    if not os.path.exists('sprites'):
        os.mkdir('sprites')
    if not os.path.exists('png'):
        os.mkdir('png')

    sc_texture = SC(_i('Texture Filename'))
    sc_texture.generate_shapes()
