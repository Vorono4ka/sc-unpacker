from utils.reader import Reader


class CustomObject:
    def to_dict(self) -> dict:
        dictionary = {}

        for key, value in self.__dict__.items():
            if key in ['buffer', 'endian', 'i']:
                continue
            if value is not None:
                value_type = type(value)

                attribute_value = None

                if value_type is list:
                    attribute_value = []
                    for item in value:
                        item_type = type(item)

                        if issubclass(item_type, CustomObject):
                            item = item.to_dict()
                        attribute_value.append(item)
                elif issubclass(value_type, CustomObject):
                    attribute_value = value.to_dict()
                elif attribute_value is None:
                    attribute_value = value

                dictionary[key] = attribute_value
        return dictionary

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        else:
            raise IndexError('The object has no attribute named ' + item)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} ({self.to_dict()})>'


class Size(CustomObject):
    def __init__(self):
        self.height = 0
        self.width = 0


class Point(CustomObject):
    def __init__(self):
        self.x: float
        self.y: float


class ScObject(Reader, CustomObject):
    def readString(self) -> str:
        length = self.readUByte()
        if length < 255:
            return self.readChar(length)
        else:
            return ''

    def __init__(self, buffer: bytes, tag: int = 0):
        super().__init__(buffer, 'little')
        self.tag = tag

    def parse(self, **kwargs):
        pass


class Export(ScObject):
    def __init__(self, buffer: bytes = b''):
        super().__init__(buffer)

        self.name = None
        self.id = 0


class Matrix(ScObject):
    def __init__(self, buffer: bytes, tag: int):
        super().__init__(buffer, tag)
        self.matrix: list

    def parse(self, **kwargs):
        v1_1 = self.readInt32() * 0.00097656
        v2_1 = self.readInt32() * 0.00097656
        v1_2 = self.readInt32() * 0.00097656
        v2_2 = self.readInt32() * 0.00097656
        v1_3 = self.readInt32() * 0.05
        v2_3 = self.readInt32() * 0.05

        setattr(self, 'matrix',
                [v1_1, v1_2, v1_3,
                 v2_1, v2_2, v2_3])


class Color(ScObject):
    def __init__(self, buffer: bytes, tag: int):
        super().__init__(buffer, tag)
        self.color: list

    def parse(self, **kwargs):
        r = self.readUShort()
        g = self.readUShort()
        b = self.readUShort()
        a = self.readUByte()

        setattr(self, 'color', [r, g, b, a])


class Texture(ScObject):
    def __init__(self, buffer: bytes, tag: int):
        super().__init__(buffer, tag)
        self.size: Size = Size()
        self.image_type: int

        self.width: int
        self.height: int

    def parse(self, **kwargs):
        setattr(self, 'image_type', self.readByte())

        setattr(self, 'width', self.readUShort())
        setattr(self, 'height', self.readUShort())
        setattr(getattr(self, 'size'), 'width', getattr(self, 'width'))
        setattr(getattr(self, 'size'), 'height', getattr(self, 'height'))


class MovieClip(ScObject):
    def __init__(self, buffer: bytes, tag: int):
        super().__init__(buffer, tag)
        self.id: int
        self.clip_fps: int
        self.frames_count: int

        self.transforms: list
        self.binds: list

    def parse(self, **kwargs):
        setattr(self, 'id', self.readUShort())
        setattr(self, 'clip_fps', self.readByte())
        setattr(self, 'frames_count', self.readUShort())

        transforms = []
        count = self.readUInt32()
        for x in range(count):
            transforms.append({})

            transforms[x]['bind_id'] = self.readUShort()
            transforms[x]['bind_matrix'] = self.readUShort()
            transforms[x]['bind_color_id'] = self.readUShort()
        setattr(self, 'transforms', transforms)

        binds = []
        count = self.readShort()
        for x in range(count):
            binds.append({})

            binds[x]['bind_id'] = self.readUShort()

        if self.tag == 12:
            for x in range(count):
                binds[x]['opacity'] = self.readByte()

        for x in range(count):
            binds[x]['bind_name'] = self.readString()
        setattr(self, 'binds', binds)

        unk_array = []
        while True:
            while True:
                while True:
                    unk_array.append({})

                    unk_tag = self.readUByte()
                    unk_length = self.readUInt32()

                    unk_array[len(unk_array) - 1]['unk_tag'] = unk_tag
                    unk_array[len(unk_array) - 1]['unk_length'] = unk_length

                    if unk_tag != 5:
                        break
                if unk_tag == 11:
                    unk_array[len(unk_array) - 1]['frame_id'] = self.readShort()
                    unk_array[len(unk_array) - 1]['frame_name'] = self.readString()
                else:
                    break
            if unk_tag == 0:
                break


class TextField(ScObject):
    def __init__(self, buffer: bytes, tag: int):
        super().__init__(buffer, tag)
        self.id: int
        self.font: str

    def parse(self, **kwargs):
        setattr(self, 'id', self.readUShort())
        setattr(self, 'font', self.readString())


class Shape(ScObject):
    def __init__(self, buffer: bytes, tag: int):
        super().__init__(buffer, tag)
        self.id: int
        self.regions_count: int
        self.points_count: int

        self.regions: list

    def parse(self, **kwargs):
        setattr(self, 'id', self.readUShort())
        setattr(self, 'regions_count', self.readUShort())
        setattr(self, 'points_count', self.readUShort())

        regions = []
        for x in range(getattr(self, 'regions_count')):
            chunk_type = self.readUByte()
            if chunk_type in [17, 22]:
                chunk_length = self.readUInt32()
                region_data = self.read(chunk_length)
                region = Region(region_data, chunk_type)
                region.parse(textures=kwargs['textures'])

                regions.append(region)
            if chunk_type == 0:
                break
        setattr(self, 'regions', regions)


class Region(ScObject):
    def __init__(self, buffer: bytes, tag: int):
        super().__init__(buffer, tag)
        self.texture_id: int
        self.points_count: int

        self.sheet_points: list
        self.shape_points: list

    def parse(self, **kwargs):
        setattr(self, 'texture_id', self.readByte())
        texture = kwargs['textures'][getattr(self, 'texture_id')]

        setattr(self, 'points_count', self.readByte())

        sheet_points = []
        for i in range(getattr(self, 'points_count')):  # sheet_points
            point = Point()

            point.x = self.readInt32() * 0.05
            point.y = self.readInt32() * 0.05

            sheet_points.append(point)
        setattr(self, 'sheet_points', sheet_points)

        shape_points = []
        for i in range(getattr(self, 'points_count')):  # sheet_points
            point = Point()

            point.x = self.readUShort()  # u
            point.y = self.readUShort()  # v

            if self.tag == 22:
                point.x /= 65535
                point.y /= 65535

                point.x *= texture.size.width
                point.y *= texture.size.height

            shape_points.append(point)
        setattr(self, 'shape_points', shape_points)
