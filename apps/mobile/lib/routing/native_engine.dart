import 'dart:convert';
import 'dart:ffi';
import 'dart:io';
import 'dart:isolate';

import 'package:ffi/ffi.dart';

import 'plan.dart';

/// The routing engine of the server, compiled for the phone (`libnemesis_routing.so`,
/// services/routing/crates/routing-ffi) : mêmes itinéraires en ligne et hors ligne.
///
/// The pack is loaded once; each plan runs in a short-lived isolate so that the screen
/// never freezes. The engine only reads its data while planning, so concurrent plans are
/// safe; it is closed with [close].
class NativeRoutingService implements RoutingService {
  NativeRoutingService._(this._library, this._engine);

  /// Opens the engine on the pack copied to [packDir].
  ///
  /// [library] is the path of the shared library on the host (tests); on Android the
  /// library packaged in the APK is found by name.
  static NativeRoutingService open(String packDir, {String? library}) {
    final path = library ?? _defaultLibrary();
    final bindings = _Bindings(DynamicLibrary.open(path));
    final dir = packDir.toNativeUtf8();
    final error = calloc<Pointer<Utf8>>();
    try {
      final engine = bindings.open(dir, error);
      if (engine == nullptr) {
        final message = error.value == nullptr
            ? 'pack illisible'
            : error.value.toDartString();
        if (error.value != nullptr) bindings.free(error.value);
        throw RoutingException(message);
      }
      return NativeRoutingService._(path, engine.address);
    } finally {
      calloc.free(dir);
      calloc.free(error);
    }
  }

  /// On Android the loader finds the library of the APK by its name; on a computer,
  /// `NEMESIS_ROUTING_LIB` gives its path.
  static String _defaultLibrary() =>
      Platform.environment['NEMESIS_ROUTING_LIB'] ?? 'libnemesis_routing.so';

  final String _library;
  final int _engine;
  bool _closed = false;

  /// Description of the pack and of the engine.
  Map<String, dynamic> info() {
    final bindings = _Bindings(DynamicLibrary.open(_library));
    final text = bindings.info(Pointer.fromAddress(_engine));
    try {
      return jsonDecode(text.toDartString()) as Map<String, dynamic>;
    } finally {
      bindings.free(text);
    }
  }

  @override
  Future<PlanResult> plan(PlanQuery query) async {
    if (_closed) throw const RoutingException('moteur fermé');
    final library = _library;
    final engine = _engine;
    final request = query.toEngineJson();
    final reply = await Isolate.run(() {
      final bindings = _Bindings(DynamicLibrary.open(library));
      final text = request.toNativeUtf8();
      try {
        final answer = bindings.plan(Pointer.fromAddress(engine), text);
        try {
          return answer.toDartString();
        } finally {
          bindings.free(answer);
        }
      } finally {
        calloc.free(text);
      }
    });
    final json = jsonDecode(reply) as Map<String, dynamic>;
    if (json['error'] case final String message) {
      throw RoutingException(message);
    }
    return PlanResult.fromJson(json['ok'] as Map<String, dynamic>);
  }

  void close() {
    if (_closed) return;
    _closed = true;
    _Bindings(DynamicLibrary.open(_library))
        .close(Pointer.fromAddress(_engine));
  }
}

final class _Engine extends Opaque {}

class _Bindings {
  _Bindings(DynamicLibrary lib)
    : open = lib
          .lookupFunction<
            Pointer<_Engine> Function(Pointer<Utf8>, Pointer<Pointer<Utf8>>),
            Pointer<_Engine> Function(Pointer<Utf8>, Pointer<Pointer<Utf8>>)
          >('nemesis_engine_open'),
      info = lib
          .lookupFunction<
            Pointer<Utf8> Function(Pointer<_Engine>),
            Pointer<Utf8> Function(Pointer<_Engine>)
          >('nemesis_engine_info'),
      plan = lib
          .lookupFunction<
            Pointer<Utf8> Function(Pointer<_Engine>, Pointer<Utf8>),
            Pointer<Utf8> Function(Pointer<_Engine>, Pointer<Utf8>)
          >('nemesis_engine_plan'),
      free = lib
          .lookupFunction<
            Void Function(Pointer<Utf8>),
            void Function(Pointer<Utf8>)
          >('nemesis_string_free'),
      close = lib
          .lookupFunction<
            Void Function(Pointer<_Engine>),
            void Function(Pointer<_Engine>)
          >('nemesis_engine_close');

  final Pointer<_Engine> Function(Pointer<Utf8>, Pointer<Pointer<Utf8>>) open;
  final Pointer<Utf8> Function(Pointer<_Engine>) info;
  final Pointer<Utf8> Function(Pointer<_Engine>, Pointer<Utf8>) plan;
  final void Function(Pointer<Utf8>) free;
  final void Function(Pointer<_Engine>) close;
}
