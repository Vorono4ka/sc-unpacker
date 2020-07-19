import json
import os
import sys
from pprint import pprint

from PIL import Image, ImageDraw


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
        self.binds = {}

        self.basename = filename.split('.sc')[0]
        self.datafile_name = self.basename + '.sc.parsed.json'
        self.datafile_path = f'parsed/{self.datafile_name}'

        self.info = json.load(open(self.datafile_path))

        self.shapes = self.info['shapes']
        self.animations = self.info['animations']
        self.textures_info = self.info['textures']
        self.text_fields = self.info['text_fields']
        self.matrices = self.info['matrices']
        self.color_transformations = self.info['color_transformations']
        self.exports = self.info['exports']['names']

        self.textures = []
        for file in os.listdir(f'png/{self.basename}_tex'):
            self.textures.append(Image.open(f'png/{self.basename}_tex/{file}'))

        print(len(self.shapes),
              len(self.animations),
              len(self.text_fields),
              len(self.matrices),
              len(self.color_transformations),
              len(self.exports))

        # for animation in self.animations:
        #     for frame in animation['frames']:
        #         for shape in self.shapes:
        #             if shape['index'] == frame['shape_id']:
        #                 if frame['bind_name'] is not None:
        #                     print(animation)
        #                     print('|-', frame['bind_name'], '-', shape, sep='')
        
        # for text_field in self.text_fields:
        #     print(text_field)

        self.clips_ids = [clip['clip_id'] for clip in self.animations]
        self.shapes_ids = [shape['index'] for shape in self.shapes]

        for shape in self.shapes:
            self.binds[shape['index']] = shape

        for clip in self.animations:
            self.binds[clip['clip_id']] = clip

        # pprint(self.binds)
        # pprint([key for key in self.binds.keys()])

        for clip in self.animations:
            self.parse_clip(clip)

        # pprint(self.binds)

        for bind_id in self.binds:
            if bind_id not in self.shapes_ids:
                clip = self.binds[bind_id]
                if 'name' in clip:
                    for bind in clip['binds']:
                        if bind['bind_id'] in self.shapes_ids:
                            shape = self.binds[bind['bind_id']]
                            self.generate_shapes(shape, clip['name'])

        # for shape in self.shapes:
        #     if shape['index'] == 4230:
        #         input(self.shapes.index(shape))
        # json.dump(self.info, open(self.datafile_path, 'w'), indent=4)

    def parse_clip(self, clip):
        for bind in clip['binds']:
            if bind['bind_id'] in self.binds:
                if 'name' not in self.binds[bind['bind_id']] or self.binds[bind['bind_id']]['name'] is None:
                    self.binds[bind['bind_id']]['name'] = bind['bind_name']

    def generate_shapes(self, shape, name):
        export_folder = f'sprites/{self.basename}/'
        if not os.path.exists(export_folder):
            os.mkdir(export_folder)

        if len(shape['regions']) > 1:
            export_folder += f'{name}'
            if not os.path.exists(export_folder):
                os.mkdir(export_folder)

        for region in shape['regions']:
            polygon = [region['sheet_points'][z] for z in range(len(region['sheet_points']))]

            polygon = [tuple(point) for point in polygon]

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

            i = 0
            if len(shape['regions']) > 1:
                export_path = f'{export_folder}/{i}_{shape["regions"].index(region)}.png'
                i += 1
            else:
                export_path = f'{export_folder}/{name}_{i}.png'

            if os.path.exists(export_path):
                i = 0
                while os.path.exists(export_path):
                    if len(shape['regions']) > 1:
                        export_path = f'{export_folder}/{i}_{shape["regions"].index(region)}.png'
                    else:
                        export_path = f'{export_folder}/{name}_{i}.png'
                    i += 1

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

    sc = SC(_i('SC Filename'))
