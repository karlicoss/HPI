from my.core import __NOT_HPI_MODULE__  # isort: skip

# NOTE: this tool was quite useful https://github.com/aj3423/aproto

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

TYPE_STRING  = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
TYPE_BYTES   = descriptor_pb2.FieldDescriptorProto.TYPE_BYTES
TYPE_UINT64  = descriptor_pb2.FieldDescriptorProto.TYPE_UINT64
TYPE_MESSAGE = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE

OPTIONAL = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
REQUIRED = descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED


def get_place_protos():
    f1 = descriptor_pb2.DescriptorProto(name='xf1')
    # TODO 2 -> 5 is address? 2 -> 6 is a pair of coordinates
    f1.field.add(name='title', number=3, type=TYPE_STRING, label=REQUIRED)
    f1.field.add(name='note' , number=4, type=TYPE_STRING, label=OPTIONAL)
    # TODO what's the difference between required and optional? doesn't impact decoding?

    ts = descriptor_pb2.DescriptorProto(name='Timestamp')
    ts.field.add(name='seconds', number=1, type=TYPE_UINT64, label=REQUIRED)
    ts.field.add(name='nanos'  , number=2, type=TYPE_UINT64, label=REQUIRED)

    f1.field.add(name='created', number=10 ,type=TYPE_MESSAGE, label=REQUIRED, type_name=ts.name)
    f1.field.add(name='updated', number=11 ,type=TYPE_MESSAGE, label=REQUIRED, type_name=ts.name)

    f2 = descriptor_pb2.DescriptorProto(name='xf2')
    f2.field.add(name='addr1', number=2, type=TYPE_STRING, label=REQUIRED)
    f2.field.add(name='addr2', number=3, type=TYPE_STRING, label=REQUIRED)
    f2.field.add(name='f21'  , number=4, type=TYPE_BYTES , label=REQUIRED)
    f2.field.add(name='f22'  , number=5, type=TYPE_UINT64, label=REQUIRED)
    f2.field.add(name='f23'  , number=6, type=TYPE_STRING, label=REQUIRED)
    # NOTE: this also contains place ID

    f3 = descriptor_pb2.DescriptorProto(name='xf3')
    # NOTE: looks like it's the same as 'updated' from above??
    f3.field.add(name='f31', number=1, type=TYPE_UINT64, label=OPTIONAL)

    descriptor_proto = descriptor_pb2.DescriptorProto(name='PlaceParser')
    descriptor_proto.field.add(name='f1', number=1, type=TYPE_MESSAGE, label=REQUIRED, type_name=f1.name)
    descriptor_proto.field.add(name='f2', number=2, type=TYPE_MESSAGE, label=REQUIRED, type_name=f2.name)
    descriptor_proto.field.add(name='f3', number=3, type=TYPE_MESSAGE, label=OPTIONAL, type_name=f3.name)
    descriptor_proto.field.add(name='f4', number=4, type=TYPE_STRING , label=OPTIONAL)
    # NOTE: f4 is the list id

    return [descriptor_proto, ts, f1, f2, f3]


def get_labeled_protos():
    address = descriptor_pb2.DescriptorProto(name='address')
    # 1: address
    # 2: parts of address (multiple)
    # 3: full address
    address.field.add(name='full', number=3, type=TYPE_STRING, label=REQUIRED)

    main = descriptor_pb2.DescriptorProto(name='LabeledParser')
    # field 1 contains item type and item id
    main.field.add(name='title'  , number=3, type=TYPE_STRING , label=REQUIRED)
    main.field.add(name='address', number=5, type=TYPE_MESSAGE, label=OPTIONAL, type_name=address.name)

    return [main, address]


def get_list_protos():
    f1 = descriptor_pb2.DescriptorProto(name='xf1')
    f1.field.add(name='name', number=5, type=TYPE_STRING, label=REQUIRED)

    main = descriptor_pb2.DescriptorProto(name='ListParser')
    main.field.add(name='f1', number=1, type=TYPE_MESSAGE, label=REQUIRED, type_name=f1.name)
    main.field.add(name='f2', number=2, type=TYPE_STRING , label=REQUIRED)

    return [main, f1]


def make_parser(main, *extras):
    file_descriptor_proto = descriptor_pb2.FileDescriptorProto(name='dynamic.proto', package='dynamic_package')
    for proto in [main, *extras]:
        file_descriptor_proto.message_type.add().CopyFrom(proto)

    pool = descriptor_pool.DescriptorPool()
    _file_descriptor = pool.Add(file_descriptor_proto)

    message_descriptor = pool.FindMessageTypeByName(f'{file_descriptor_proto.package}.{main.name}')
    factory = message_factory.MessageFactory(pool)
    dynamic_message_class = factory.GetPrototype(message_descriptor)  # type: ignore[attr-defined]

    return dynamic_message_class


place_parser_class   = make_parser(*get_place_protos())
labeled_parser_class = make_parser(*get_labeled_protos())
list_parser_class    = make_parser(*get_list_protos())


def parse_place(blob: bytes):
    m = place_parser_class()
    m.ParseFromString(blob)
    return m


def parse_labeled(blob: bytes):
    m = labeled_parser_class()
    m.ParseFromString(blob)
    return m


def parse_list(blob: bytes):
    msg = list_parser_class()
    msg.ParseFromString(blob)
    return msg
