# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings

import video_file_pb2 as video__file__pb2

GRPC_GENERATED_VERSION = '1.69.0'
GRPC_VERSION = grpc.__version__
_version_not_supported = False

try:
    from grpc._utilities import first_version_is_lower
    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True

if _version_not_supported:
    raise RuntimeError(
        f'The grpc package installed is at version {GRPC_VERSION},'
        + f' but the generated code in video_file_pb2_grpc.py depends on'
        + f' grpcio>={GRPC_GENERATED_VERSION}.'
        + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}'
        + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.'
    )


class VideoServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.UploadVideo = channel.stream_unary(
                '/video.VideoService/UploadVideo',
                request_serializer=video__file__pb2.VideoChunk.SerializeToString,
                response_deserializer=video__file__pb2.UploadResponse.FromString,
                _registered_method=True)
        self.DownloadVideo = channel.unary_stream(
                '/video.VideoService/DownloadVideo',
                request_serializer=video__file__pb2.VideoRequest.SerializeToString,
                response_deserializer=video__file__pb2.VideoChunk.FromString,
                _registered_method=True)


class VideoServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def UploadVideo(self, request_iterator, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def DownloadVideo(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_VideoServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'UploadVideo': grpc.stream_unary_rpc_method_handler(
                    servicer.UploadVideo,
                    request_deserializer=video__file__pb2.VideoChunk.FromString,
                    response_serializer=video__file__pb2.UploadResponse.SerializeToString,
            ),
            'DownloadVideo': grpc.unary_stream_rpc_method_handler(
                    servicer.DownloadVideo,
                    request_deserializer=video__file__pb2.VideoRequest.FromString,
                    response_serializer=video__file__pb2.VideoChunk.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'video.VideoService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('video.VideoService', rpc_method_handlers)


 # This class is part of an EXPERIMENTAL API.
class VideoService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def UploadVideo(request_iterator,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.stream_unary(
            request_iterator,
            target,
            '/video.VideoService/UploadVideo',
            video__file__pb2.VideoChunk.SerializeToString,
            video__file__pb2.UploadResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def DownloadVideo(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_stream(
            request,
            target,
            '/video.VideoService/DownloadVideo',
            video__file__pb2.VideoRequest.SerializeToString,
            video__file__pb2.VideoChunk.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)
