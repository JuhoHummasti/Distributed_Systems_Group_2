# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: file-storage-service.proto
# Protobuf Python Version: 5.29.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    5,
    29,
    0,
    '',
    'file-storage-service.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x1a\x66ile-storage-service.proto\x12\x0c\x66ile_storage\"+\n\x17VideoDownloadUrlRequest\x12\x10\n\x08video_id\x18\x01 \x01(\t\"0\n\x18VideoDownloadUrlResponse\x12\x14\n\x0c\x64ownload_url\x18\x01 \x01(\t2z\n\x12\x46ileStorageService\x12\x64\n\x13GetVideoDownloadUrl\x12%.file_storage.VideoDownloadUrlRequest\x1a&.file_storage.VideoDownloadUrlResponseb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'file_storage_service_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_VIDEODOWNLOADURLREQUEST']._serialized_start=44
  _globals['_VIDEODOWNLOADURLREQUEST']._serialized_end=87
  _globals['_VIDEODOWNLOADURLRESPONSE']._serialized_start=89
  _globals['_VIDEODOWNLOADURLRESPONSE']._serialized_end=137
  _globals['_FILESTORAGESERVICE']._serialized_start=139
  _globals['_FILESTORAGESERVICE']._serialized_end=261
# @@protoc_insertion_point(module_scope)
