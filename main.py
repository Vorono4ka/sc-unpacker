import os
import sys

from PIL import Image, ImageDraw
from sc_compression.compression import Decompressor

from utils.chunks import Export, Texture, Shape, MovieClip, TextField, Matrix, Color, ScObject
from utils.chunks import CustomObject
from utils.reader import Reader


def progressbar(current, total, message):
    sys.stdout.write(f"\r[{percent(current, total)}%] {message}")


def percent(current, total):
    return (current + 1) * 100 // total


def join_image(img, p):
    _w, _h = img.size
    imgl = img.load()
    x = 0
    a = 32

    _ha = _h // a
    _wa = _w // a
    ha = _h % a
    wa = _w % a

    for l in range(_ha):
        for k in range(_wa):
            for j in range(a):
                for h in range(a):
                    imgl[h + k * a, j + l * a] = p[x]
                    x += 1

        for j in range(a):
            for h in range(wa):
                imgl[h + (_w - wa), j + l * a] = p[x]
                x += 1
        progressbar(l, _ha, 'Joining picture...')

    for k in range(_wa):
        for j in range(ha):
            for h in range(a):
                imgl[h + k * a, j + (_h - ha)] = p[x]
                x += 1

    for j in range(ha):
        for h in range(wa):
            imgl[h + (_w - wa), j + (_h - ha)] = p[x]
            x += 1
    progressbar(l, _ha, 'Joining picture...')
    print()


class SC(ScObject):
    def readPixel(self, pixel_type) -> tuple:
        if pixel_type == 0:
            r = self.readUByte()
            g = self.readUByte()
            b = self.readUByte()
            a = self.readUByte()
            return r, g, b, a
        elif pixel_type == 2:
            pixel = self.readUShort()
            r = ((pixel >> 12) & 0xF) << 4
            g = ((pixel >> 8) & 0xF) << 4
            b = ((pixel >> 4) & 0xF) << 4
            a = ((pixel >> 0) & 0xF) << 4
            return r, g, b, a
        elif pixel_type == 4:
            pixel = self.readUShort()
            r = ((pixel >> 11) & 0x1F) << 3
            g = ((pixel >> 5) & 0x3F) << 2
            b = (pixel & 0x1F) << 3
            return r, g, b
        elif pixel_type == 6:
            pixel = self.readUShort()
            r = (pixel >> 8)
            g = (pixel >> 8)
            b = (pixel >> 8)
            a = (pixel & 0xFF)
            return r, g, b, a
        elif pixel_type == 10:
            pixel = self.readUByte()
            r = pixel
            g = pixel
            b = pixel
            return r, g, b

    def __init__(self, filename: str):
        self.basename = os.path.splitext(filename)[0]

        with open(f'sc/{filename}', 'rb') as fh:
            buffer = fh.read()
            fh.close()

        decompressor = Decompressor()
        buffer = decompressor.decompress(buffer)

        Reader.__init__(self, buffer, 'little')

        self.is_texture = self.basename.endswith('_tex')
        if self.is_texture:
            if not os.path.exists('png'):
                os.mkdir('png')

        self.shape_count: int = 0
        self.clips_count: int = 0
        self.textures_count: int = 0
        self.text_fields_count: int = 0
        self.matrix_count: int = 0
        self.color_transformations_count: int = 0

        self.shapes: list = []
        self.clips: list = []
        self.textures: list = []
        self.text_fields: list = []
        self.matrix: list = []
        self.color_transformations: list = []

        self.exports: list = []

    def parse(self):
        if self.is_texture:
            export_folder = 'png/' + self.basename + '/'

            if not os.path.exists(export_folder):
                os.mkdir(export_folder)

            i = 0
            while len(self.buffer[self.tell():]) > 10:
                file_type = self.readUByte()
                file_size = self.readUInt32()
                pixel_type = self.readUByte()
                width = self.readUShort()
                height = self.readUShort()

                pixels = []
                for y in range(height):
                    for x in range(width):
                        pixels.append(self.readPixel(pixel_type))
                        progressbar(len(pixels), width * height, 'Creating picture...')

                if pixel_type in range(4):
                    img_format = 'RGBA'
                elif pixel_type == 4:
                    img_format = 'RGB'
                elif pixel_type == 6:
                    img_format = 'LA'
                elif pixel_type == 10:
                    img_format = 'L'
                else:
                    raise TypeError('Ban.')

                image = Image.new(img_format, (width, height))

                image.putdata(pixels)

                if file_type in [27, 28]:
                    join_image(image, pixels)

                export_path = export_folder + self.basename + '_' * i + '.png'

                image.save(export_path)
                i += 1
        else:
            self.shape_count = self.readUShort()
            self.clips_count = self.readUShort()
            self.textures_count = self.readUShort()
            self.text_fields_count = self.readUShort()
            self.matrix_count = self.readUShort()
            self.color_transformations_count = self.readUShort()

            self.readInt32()
            self.readByte()

            exports_count = self.readUShort()
            for x in range(exports_count):
                self.exports.append(Export())

                self.exports[x].id = self.readUShort()
            for x in range(exports_count):
                self.exports[x].name = self.readString()

            while len(self.buffer[self.tell():]) >= 5:
                progressbar(len(self.buffer) - len(self.buffer[self.tell():]), len(self.buffer),
                            'Data Parsing...')

                tag = self.readUByte()
                length = self.readUInt32()
                data = self.read(length)

                if tag in [1, 16, 28, 29, 34]:  # Texture
                    texture = Texture(data, tag)
                    texture.parse()

                    self.textures.append(texture)
                elif tag in [2, 18]:  # Shape Id
                    shape = Shape(data, tag)
                    shape.parse(textures=self.textures)

                    self.shapes.append(shape)
                elif tag in [3, 10, 12, 14]:  # MovieClip
                    movie_clip = MovieClip(data, tag)
                    movie_clip.parse()

                    self.clips.append(movie_clip)
                elif tag in [7, 15, 20, 21, 25, 33]:  # Text Fields
                    text_field = TextField(data, tag)
                    text_field.parse()

                    self.text_fields.append(text_field)
                elif tag in [8]:  # Matrix
                    matrix = Matrix(data, tag)
                    matrix.parse()

                    self.matrix.append(matrix)
                elif tag in [9]:  # Color Transformation
                    color = Color(data, tag)
                    color.parse()

                    self.color_transformations.append(color)
                # elif tag in [13]:
                #     pass
                # elif tag in [19, 24, 27]:
                #     pass
                # elif tag in [23]:
                #     pass
                # elif tag in [26]:
                #     pass
                # elif tag in [30]:
                #     pass
                # elif tag in [32]:
                #     pass
                # else:
                #     print(tag, data)

            print()
            print('-' * 30)

            print(f'Shapes: {len(self.shapes) == self.shape_count}',
                  f'Clips: {len(self.clips) == self.clips_count}',
                  f'Textures: {len(self.textures) == self.textures_count}',
                  f'Text Fields: {len(self.text_fields) == self.text_fields_count}',
                  f'Matrix: {len(self.matrix) == self.matrix_count}',
                  f'Color Transforms: {len(self.color_transformations) == self.color_transformations_count}',
                  sep='\n')


class Unpacker(CustomObject):
    def __init__(self, data: SC):
        self.export_path = 'sprites'
        self.textures = []
        self.binds = []

        textures_path = 'png/' + data.basename + '_tex/'
        for file in os.listdir(textures_path):
            texture = Image.open(open(textures_path + file, 'rb'))
            self.textures.append(texture)

        data.clips = {clip.id: clip for clip in data.clips}
        data.shapes = {shape.id: shape for shape in data.shapes}
        data.text_fields = {text_field.id: text_field for text_field in data.text_fields}
        self.data = data

        for export in self.data.exports:
            self.parse_export(export)

    def parse_export(self, export: Export):
        export_name = export.name
        export_id = export.id
        self.binds = {}

        self.export_path = 'sprites/' + self.data.basename + '/' + export_name + '/'

        clip = self.data.clips[export_id]

        del clip.transforms[1:]
        del clip.binds[1:]

        print(export_name, '-->', clip)
        regions = self.parse_movie_clip(clip)
        self.save_region(regions, '')

    def parse_movie_clip(self, clip):
        regions = []

        for bind in clip.binds:
            bind_id = bind['bind_id']
            if bind_id in self.data.clips:
                bind_data = self.data.clips[bind_id]
                to_append_regions = self.parse_movie_clip(bind_data)
                regions.append(to_append_regions)
            elif bind_id in self.data.shapes:
                shape = self.data.shapes[bind_id]

                for region in shape.regions:
                    region = self.draw_region(region)
                    regions.append(region)
            elif bind_id in self.data.text_fields:
                text_field = self.data.text_fields[bind_id]
            else:
                print(bind_id)

        return regions

    def draw_region(self, region):
        texture = self.textures[region.texture_id]

        polygon = [(round(point.x), round(point.y)) for point in region.shape_points]
        size = (
            texture.size[0],
            texture.size[1]
        )

        imMask = Image.new('L', size, 0)
        ImageDraw.Draw(imMask).polygon(polygon, fill=255)
        bbox = imMask.getbbox()
        if bbox is None:
            polygon[2:] = [(point[0] + 1, point[1] + 1) for point in polygon[2:]]
            ImageDraw.Draw(imMask).polygon(polygon, fill=255)
            bbox = imMask.getbbox()
        region_size = (bbox[2] - bbox[0], bbox[3] - bbox[1])
        tmpRegion = Image.new('RGBA', region_size, None)
        tmpRegion.paste(texture.crop(bbox), None, imMask.crop(bbox))

        return tmpRegion

    def save_region(self, region, export_name):
        if not os.path.exists(self.export_path):
            os.makedirs(self.export_path)

        if type(region) is list:
            for sub_region_index in range(len(region)):
                self.save_region(
                    region[sub_region_index],
                    str(sub_region_index) + export_name
                )
        else:
            region.save(self.export_path + str(export_name) + '.png')


if __name__ == '__main__':
    if not os.path.exists('sc'):
        os.mkdir('sc')

    # sc = SC('sc_name_tex.sc')
    # sc.parse()

    # sc = SC('sc_name.sc')
    # sc.parse()

    print()
    print()

    unpacker = Unpacker(sc)
