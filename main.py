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


class Debugger:
    def __init__(self, print_debug_info: bool = True):
        self.print_debug_info = print_debug_info

    def _w(self, *args):
        if self.print_debug_info:
            print('[Warning] ', end='')
            for arg in args:
                print(arg, end=' ')
            print()

    def _wi(self, data):
        if self.print_debug_info:
            print('[Warning] ', end='')
            return input(f'{data}: ')


def region_rotation(region):
    def calculate_summary(points):
        x1, y1 = points[(z + 1) % len(region['sheet_points'])]
        x2, y2 = points[z]
        summary = (x1 - x2) * (y1 + y2)
        return summary

    summSheet = 0
    summShape = 0

    for z in range(len(region['sheet_points'])):
        summSheet += calculate_summary(region['sheet_points'])
        summShape += calculate_summary(region['shape_points'])

    sheetOrientation = -1 if (summSheet < 0) else 1
    shapeOrientation = -1 if (summShape < 0) else 1

    region['mirroring'] = not (shapeOrientation == sheetOrientation)

    if region['mirroring']:
        for x in range(len(region['shape_points '])):
            points = region['shape_points'][x]
            region['shape_points'][x] = (points[0] * -1, points[1])

    sheet_pointX = region['sheet_points'][0]
    sheet_pointY = region['sheet_points'][1]
    shape_pointX = region['shape_points'][0]
    shape_pointY = region['shape_points'][1]

    if sheet_pointY[0] > sheet_pointX[0]:
        px = 1
    elif sheet_pointY[0] < sheet_pointX[0]:
        px = 2
    else:
        px = 3

    if sheet_pointY[1] < sheet_pointX[1]:
        py = 1
    elif sheet_pointY[1] > sheet_pointX[1]:
        py = 2
    else:
        py = 3

    if shape_pointY[0] > shape_pointX[0]:
        qx = 1
    elif shape_pointY[0] < shape_pointX[0]:
        qx = 2
    else:
        qx = 3

    if shape_pointY[1] > shape_pointX[1]:
        qy = 1
    elif shape_pointY[1] < shape_pointX[1]:
        qy = 2
    else:
        qy = 3

    print(px, py, qx, qy)

    rotation = 0

    if px == qx and py == qy:
        rotation = 0
    elif px == 3:
        if px == qy:
            if py == qx:
                rotation = 1
            else:
                rotation = 3
        else:
            rotation = 2
    elif py == 3:
        if py == qx:
            if px == qy:
                rotation = 3
            else:
                rotation = 1
        else:
            rotation = 2
    elif px != qx and py != qy:
        rotation = 2
    elif px == py:
        if px != qx:
            rotation = 3
        elif py != qy:
            rotation = 1
    elif px != py:
        if px != qx:
            rotation = 1
        elif py != qy:
            rotation = 3

    if sheetOrientation == -1 and rotation in (1, 3):
        rotation += 2
        rotation %= 4

    region['rotation'] = rotation * 90
    return region


class SC(Reader):
    def readString(self):
        length = self.readUByte()
        if length < 255:
            return self.readChar(length)
        else:
            return ''

    def __init__(self, filename: str,
                 compressed: bool = True,
                 save_decompressed: bool = True,
                 print_debug_info: bool = False,
                 sheets: list = None):
        self.debugger = Debugger(print_debug_info)
        self.sheets = sheets

        self.base_name = filename.split('.sc')[0]
        self.is_texture = self.base_name.endswith('_tex')
        if not self.is_texture:
            self.sc_data = {}

            self.shapes = []
            self.animations = []
            self.textures = []
            self.text_fields = []
            self.matrices = []
            self.color_transformations = []

            self.exports = {'names': []}

            self.shape_count = 0
            self.animations_count = 0
            self.textures_count = 0
            self.text_fields_count = 0
            self.matrix_count = 0
            self.color_transformations_count = 0
        else:
            self.sheets = []

            self.data_name = self.base_name[:-4] + '.sc'
        self.filename = filename

        if compressed:
            with open('compressed/' + filename, 'rb') as file:
                self.data = file.read()

                file.close()

            self.decompress(save_decompressed)
        else:
            with open('decompressed/' + filename, 'rb') as file:
                self.data = file.read()

                file.close()

        super().__init__(self.data, '<')

    def convert_pixel(self, pixel_type):
        if pixel_type == 0:  # RGB8888
            return self.readUByte(), self.readUByte(), self.readUByte(), self.readUByte()
        elif pixel_type == 2:  # RGB4444
            pixel = self.readUShort()
            return (((pixel >> 12) & 0xF) << 4, ((pixel >> 8) & 0xF) << 4,
                    ((pixel >> 4) & 0xF) << 4, ((pixel >> 0) & 0xF) << 4)
        elif pixel_type == 4:  # RGB565
            pixel = self.readUShort()
            return ((pixel >> 11) & 0x1F) << 3, ((pixel >> 5) & 0x3F) << 2, (pixel & 0x1F) << 3
        elif pixel_type == 6:  # LA88
            pixel = self.readUShort()
            return (pixel >> 8), (pixel >> 8), (pixel >> 8), (pixel & 0xFF)
        elif pixel_type == 10:  # L8
            pixel = self.readUByte()
            return pixel, pixel, pixel

    def decompress(self, save_decompressed: bool):
        if self.data[0] != 93:
            self.data = self.data[26:]
        xbytes = b'\xff' * 8

        data = self.data[0:5] + xbytes + self.data[9:]
        decompressor = lzma.LZMADecompressor()
        decompressed = decompressor.decompress(data)

        if save_decompressed:
            with open('decompressed/' + self.filename, 'wb') as file:
                file.write(decompressed)

                file.close()

        self.data = decompressed

    def parse(self, save_parsed_data: bool = False,
              save_texture: bool = True):
        # try:
        if self.is_texture:
            filename = self.filename.split('.sc')[0]
            picture_index = 0

            if not os.path.exists(f'png/{filename}'):
                os.mkdir(f'png/{filename}')
            while len(self.data[self.tell():]) > 5:
                pixels = []

                file_type = self.readUByte()
                if file_type != 0:
                    file_size = self.readUInt32()
                    pixel_type = self.readUByte()
                    width = self.readUShort()
                    height = self.readUShort()

                    _(f'File Size: {round(file_size / 8 / 1024 / 1024, 2)}Mb, Width: {width}, Height: {height}')

                    img = Image.new('RGBA', (width, height))

                    for y in range(height):
                        for x in range(width):
                            pixels.append(self.convert_pixel(pixel_type))

                    img.putdata(pixels)

                    if file_type in [27, 28]:
                        imgl = img.load()
                        iSrcPix = 0
                        for l in range(int(height / 32)):
                            for k in range(int(width / 32)):
                                for j in range(32):
                                    for h in range(32):
                                        imgl[h + (k * 32), j + (l * 32)] = pixels[iSrcPix]
                                        iSrcPix += 1
                            for j in range(32):
                                for h in range(width % 32):
                                    imgl[h + (width - (width % 32)), j + (l * 32)] = pixels[iSrcPix]
                                    iSrcPix += 1

                        for k in range(int(width / 32)):
                            for j in range(int(height % 32)):
                                for h in range(32):
                                    imgl[h + (k * 32), j + (height - (height % 32))] = pixels[iSrcPix]
                                    iSrcPix += 1

                        for j in range(height % 32):
                            for h in range(width % 32):
                                imgl[h + (width - (width % 32)), j + (height - (height % 32))] = pixels[iSrcPix]
                                iSrcPix += 1

                    export_name = filename + '_' * picture_index
                    picture_index += 1

                    self.sheets.append(img)

                    if save_texture:
                        img.save(f'png/{filename}/{export_name}.png', 'PNG')
        else:
            self.shape_count = self.readUShort()
            self.animations_count = self.readUShort()
            self.textures_count = self.readUShort()
            self.text_fields_count = self.readUShort()
            self.matrix_count = self.readUShort()
            self.color_transformations_count = self.readUShort()

            self.read(5)

            exports_count = self.readUShort()
            for x in range(exports_count):
                self.readUShort()

            for x in range(exports_count):
                export_name = self.readString()
                if export_name != '':
                    self.exports['names'].append(export_name)

            divider = 1

            while len(self.data[self.tell():]) != 0:
                data_type = self.readUByte()
                data_length = self.readUInt32()
                if data_type in [1, 24]:  # texture
                    pixel_type = self.readByte()

                    width = self.readUShort()
                    height = self.readUShort()

                    if self.sheets is not None:
                        if self.sheets[len(self.textures)].size != (width, height):
                            divider = 2
                        else:
                            divider = 1

                    self.textures.append({
                        'pixel_type': pixel_type,
                        'size': (width,
                                 height)
                    })
                elif data_type == 7:  # text_field
                    another_data = []
                    index = self.readUShort()
                    font_name = self.readString()
                    another_data.append(self.readUInt32())
                    self.read(6)  # another_data.append(self.read(6))
                    another_data.append(self.readUInt32())
                    self.read(5)  # another_data.append(self.read(5))
                    self.readString()

                    self.text_fields.append({
                        'index': index,
                        'font': font_name,
                        'another_data': another_data
                    })
                elif data_type == 8:  # matrix
                    matrix = []
                    for x in range(6):
                        matrix.append(self.readInt32())

                    self.matrices.append(matrix)
                elif data_type == 9:  # color_transformation
                    r = self.readUShort()
                    g = self.readUShort()
                    b = self.readUShort()
                    a = self.readUByte()

                    self.color_transformations.append((r, g, b, a))
                elif data_type == 11:
                    self.readUShort()
                    self.readString()
                elif data_type in [12, 35]:  # animation
                    frames = []

                    clip_id = self.readUShort()
                    clip_fps = self.readByte()
                    frames_count = self.readUShort()

                    cnt1 = self.readUInt32()
                    for x in range(cnt1):
                        self.readUShort()  # animation  # saTag12Nr =
                        self.readUShort()  # bind_matrix  # saTag08Nr =
                        self.readUShort()  # bind_color_transformation  # saTag09Nr =

                    cnt2 = self.readShort()
                    for x in range(cnt2):
                        bind_id = self.readUShort()

                        frames.append({
                            'bind_id': bind_id,
                            'opacity': None,
                            'bind_name': None
                        })

                    for x in range(cnt2):
                        opacity = self.readByte()

                        frames[x]['opacity'] = opacity

                    for x in range(cnt2):
                        string = self.readString()
                        if string != '':
                            frames[x]['bind_name'] = string

                    self.animations.append({
                        'clip_id': clip_id,
                        'fps': clip_fps,
                        'frames_count': frames_count,
                        'frames': frames
                    })
                elif data_type == 18:
                    regions = []

                    shape_id = self.readUShort()
                    regions_count = self.readUShort()
                    points_count = self.readUShort()

                    for x in range(regions_count):
                        data_block_tag16 = self.readUByte()
                        if data_block_tag16 == 22:
                            self.readUInt32()  # data_block_size16 =
                            sheet_id = self.readByte()

                            sheet_data = {
                                'sheet_id': sheet_id,
                                'shape_points': [],
                                'sheet_points': []
                            }

                            num_points = self.readByte()
                            for i in range(num_points):
                                x = self.readInt32()
                                y = self.readInt32()

                                sheet_data['shape_points'].append(
                                    (x, y)
                                )

                            for i in range(num_points):
                                x = self.readUShort()
                                y = self.readUShort()

                                sheet_data['sheet_points'].append(
                                    (int(round(x * self.textures[sheet_id]['size'][0] / 65535) / divider),
                                     int(round(y * self.textures[sheet_id]['size'][1] / 65535) / divider))
                                )

                            regions.append(sheet_data)
                    self.read(5)

                    self.shapes.append({
                        'index': shape_id,
                        'points_count': points_count,
                        'regions': regions
                    })
                elif data_type == 33:  # text_field
                    another_data = []
                    index = self.readUShort()
                    font_name = self.readString()
                    another_data.append(self.readUInt32())
                    self.read(15)  # another_data.append(self.read(15))
                    another_data.append(self.readString())
                    self.read(9)  # another_data.append(self.read(9))

                    self.text_fields.append({
                        'index': index,
                        'font': font_name,
                        'another_data': another_data
                    })
                elif data_type == 44:  # text_field
                    another_data = []
                    index = self.readUShort()
                    font_name = self.readString()
                    another_data.append(self.readUInt32())
                    self.read(15)  # another_data.append(self.read(15))
                    another_data.append(self.readString())
                    self.read(12)  # another_data.append(self.read(12))

                    self.text_fields.append({
                        'index': index,
                        'font': font_name,
                        'another_data': another_data
                    })
                else:
                    self.read(data_length)

            for x in range(self.shape_count):
                for y in range(len(self.shapes[x]['regions'])):

                    region = self.shapes[x]['regions'][y]

                    regionMinX = 32767
                    regionMaxX = -32767
                    regionMinY = 32767
                    regionMaxY = -32767
                    for z in range(len(region['sheet_points'])):
                        tmpX, tmpY = region['sheet_points'][z]

                        if tmpX < regionMinX:
                            regionMinX = tmpX
                        if tmpX > regionMaxX:
                            regionMaxX = tmpX
                        if tmpY < regionMinY:
                            regionMinY = tmpY
                        if tmpY > regionMaxY:
                            regionMaxY = tmpY

                    region = region_rotation(region)

                    tmpX, tmpY = regionMaxX - regionMinX, regionMaxY - regionMinY
                    size = (tmpX, tmpY)

                    if region['rotation'] in (90, 270):
                        size = size[::-1]

                    region['size'] = size

                self.shapes[x]['regions'][y] = region

            self.sc_data = {'shapes': self.shapes,
                            'animations': self.animations,
                            'textures': self.textures,
                            'text_fields': self.text_fields,
                            'matrices': self.matrices,
                            'color_transformations': self.color_transformations,

                            'exports': self.exports}

            print(f'shape_count = len(self.shapes)? - {self.shape_count == len(self.shapes)}\n',
                  f'animations_count = len(animations)? - {self.animations_count == len(self.animations)}\n',
                  f'textures_count = len(textures)? - {self.textures_count == len(self.textures)}\n',
                  f'text_fields_count = len(text_fields)? - {self.text_fields_count == len(self.text_fields)}\n',
                  f'matrix_count = len(matrices)? - {self.matrix_count == len(self.matrices)}\n',
                  f'color_transforms_count = len(color_transforms)? - ',
                  self.color_transformations_count == len(self.color_transformations), '\n', sep='')
            if save_parsed_data:
                json.dump(self.sc_data, open(f'parsed/{self.filename}.parsed.json', 'w'), indent=4)
        # except Exception as e:
        #     _e(e.with_traceback(e.__traceback__))

    def generate_shapes(self):
        export_folder = f'sprites/{self.filename.split(".sc")[0]}/'
        if not os.path.exists(export_folder):
            os.mkdir(export_folder)

        for x in range(len(self.shapes)):
            for y in range(len(self.shapes[x]['regions'])):
                region = self.shapes[x]['regions'][y]

                polygon = [region['sheet_points'][z] for z in range(len(region['sheet_points']))]

                polygon = [tuple(point) for point in polygon]

                imMask = Image.new('L', self.textures[region['sheet_id']]['size'], 0)
                ImageDraw.Draw(imMask).polygon(polygon, fill=255)
                bbox = imMask.getbbox()
                if not bbox:
                    continue

                region_size = (bbox[2] - bbox[0], bbox[3] - bbox[1])
                tmpRegion = Image.new('RGBA', region_size, None)

                tmpRegion.paste(self.sheets[region['sheet_id']].crop(bbox), None, imMask.crop(bbox))
                if region['mirroring']:
                    tmpRegion = tmpRegion.transform(region_size, Image.EXTENT, (region_size[0], 0, 0, region_size[1]))

                tmpRegion.rotate(region['rotation'], expand=True).save(f'{export_folder}/{x}_{y}.png')


if __name__ == '__main__':
    if not os.path.exists('decompressed'):
        os.mkdir('decompressed')
    if not os.path.exists('compressed'):
        os.mkdir('compressed')

    if not os.path.exists('sprites'):
        os.mkdir('sprites')

    if not os.path.exists('parsed'):
        os.mkdir('parsed')

    if not os.path.exists('png'):
        os.mkdir('png')

    sc = SC(_i('SC Filename'))
    sc.parse(True)

    if sc.is_texture:
        if sc.data_name in os.listdir('compressed'):  # background_retropolis.sc
            sc = SC(sc.data_name, True, False, True, sc.sheets)
            sc.parse(True)

            sc.generate_shapes()
        else:
            _('Файл данных отсутствует в папке, генерация атласа не будет произведена!')
