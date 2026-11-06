//! C interface of the routing engine, for the phone (I0.11, ADR-001).
//!
//! The phone loads `libnemesis_routing.so` with `dart:ffi` and calls the same McRAPTOR
//! engine as the server, on the city pack it carries: itineraries are identical online and
//! offline. Everything crosses the boundary as UTF-8 JSON in C strings:
//!
//! - `nemesis_engine_open(pack_dir, &error)` loads a pack; on failure it returns null and
//!   sets `error` to a message the caller frees;
//! - `nemesis_engine_info(engine)` describes the pack and the engine;
//! - `nemesis_engine_plan(engine, request)` takes `{"from", "to", "date", "time"}` (places
//!   as « lat,lon » or a stop name, date as AAAAMMJJ, time in seconds since midnight) and
//!   returns `{"ok": {...}}`, the same document as `routing plan`, or `{"error": "..."}`;
//! - every returned string is freed with `nemesis_string_free`, the engine with
//!   `nemesis_engine_close`.
//!
//! The functions never unwind across the boundary: a panic becomes an error message.

use std::ffi::{CStr, CString, c_char};
use std::panic::{AssertUnwindSafe, catch_unwind};
use std::path::Path;
use std::ptr;
use std::time::Instant;

use routing_core::engine::{
    DEFAULT_VIRTUAL_SPACING_M, EngineInfo, McRaptorEngine, PlanRequest, PlanResponse, RoutingEngine,
};
use serde::{Deserialize, Serialize};

/// An engine loaded on a pack, owned by the caller between open and close.
pub struct Engine {
    inner: McRaptorEngine,
}

#[derive(Debug, Deserialize)]
struct Request {
    from: String,
    to: String,
    date: u32,
    time: u32,
}

#[derive(Serialize)]
struct PlanOutput<'a> {
    engine: &'a EngineInfo,
    from: String,
    to: String,
    computed_ms: f64,
    #[serde(flatten)]
    response: PlanResponse,
}

#[derive(Serialize)]
#[serde(rename_all = "lowercase")]
enum Reply<T> {
    Ok(T),
    Error(String),
}

/// Loads the pack in `dir`.
///
/// # Errors
/// Unreadable pack.
pub fn open(dir: &Path) -> Result<Engine, String> {
    McRaptorEngine::load(dir, Some(DEFAULT_VIRTUAL_SPACING_M))
        .map(|inner| Engine { inner })
        .map_err(|e| e.to_string())
}

/// Plans a JSON request; the reply is JSON in every case.
#[must_use]
pub fn plan_json(engine: &Engine, request: &str) -> String {
    let reply = match plan(engine, request) {
        Ok(output) => serde_json::to_string(&Reply::Ok(output)),
        Err(message) => serde_json::to_string(&Reply::<()>::Error(message)),
    };
    reply.unwrap_or_else(|e| format!("{{\"error\":\"réponse illisible : {e}\"}}"))
}

fn plan<'a>(engine: &'a Engine, request: &str) -> Result<PlanOutput<'a>, String> {
    let request: Request =
        serde_json::from_str(request).map_err(|e| format!("requête illisible : {e}"))?;
    let (from, from_name) = engine.inner.resolve(&request.from)?;
    let (to, to_name) = engine.inner.resolve(&request.to)?;
    let started = Instant::now();
    let response = engine
        .inner
        .plan(&PlanRequest {
            from,
            to,
            date: request.date,
            time: request.time,
        })
        .map_err(|e| e.to_string())?;
    Ok(PlanOutput {
        engine: engine.inner.info(),
        from: from_name,
        to: to_name,
        computed_ms: started.elapsed().as_secs_f64() * 1000.0,
        response,
    })
}

fn c_string(text: String) -> *mut c_char {
    // Interior NUL bytes cannot occur in JSON produced by serde; replace them anyway.
    CString::new(text.replace('\0', " ")).map_or(ptr::null_mut(), CString::into_raw)
}

fn guarded<T>(fallback: T, body: impl FnOnce() -> T) -> T {
    catch_unwind(AssertUnwindSafe(body)).unwrap_or(fallback)
}

/// Opens the pack in `pack_dir`; null on failure, with the message in `*error` when
/// `error` is not null.
///
/// # Safety
/// `pack_dir` is a NUL-terminated UTF-8 string; `error` is null or points to writable
/// memory for one pointer. The returned engine is closed with `nemesis_engine_close`.
#[allow(unsafe_code)]
#[unsafe(no_mangle)]
pub unsafe extern "C" fn nemesis_engine_open(
    pack_dir: *const c_char,
    error: *mut *mut c_char,
) -> *mut Engine {
    let outcome = guarded(Err("panique pendant le chargement".to_owned()), || {
        if pack_dir.is_null() {
            return Err("dossier du pack absent".to_owned());
        }
        // SAFETY: the caller passes a valid NUL-terminated string (contract above).
        let dir = unsafe { CStr::from_ptr(pack_dir) }
            .to_str()
            .map_err(|e| format!("chemin illisible : {e}"))?;
        open(Path::new(dir))
    });
    match outcome {
        Ok(engine) => Box::into_raw(Box::new(engine)),
        Err(message) => {
            if !error.is_null() {
                // SAFETY: `error` points to writable memory for one pointer (contract).
                unsafe { *error = c_string(message) };
            }
            ptr::null_mut()
        }
    }
}

/// Description of the pack and of the engine, as JSON.
///
/// # Safety
/// `engine` comes from `nemesis_engine_open` and is not closed yet.
#[allow(unsafe_code)]
#[unsafe(no_mangle)]
pub unsafe extern "C" fn nemesis_engine_info(engine: *const Engine) -> *mut c_char {
    if engine.is_null() {
        return c_string("{\"error\":\"moteur absent\"}".to_owned());
    }
    // SAFETY: a live engine from `nemesis_engine_open` (contract above).
    let engine = unsafe { &*engine };
    c_string(serde_json::to_string(engine.inner.info()).unwrap_or_default())
}

/// Plans the JSON `request` and returns the JSON reply (see the module documentation).
///
/// # Safety
/// `engine` comes from `nemesis_engine_open` and is not closed yet; `request` is a
/// NUL-terminated UTF-8 string. The reply is freed with `nemesis_string_free`.
#[allow(unsafe_code)]
#[unsafe(no_mangle)]
pub unsafe extern "C" fn nemesis_engine_plan(
    engine: *const Engine,
    request: *const c_char,
) -> *mut c_char {
    let reply = guarded(
        "{\"error\":\"panique pendant le calcul\"}".to_owned(),
        || {
            if engine.is_null() || request.is_null() {
                return "{\"error\":\"moteur ou requête absent\"}".to_owned();
            }
            // SAFETY: both pointers satisfy the contract above.
            let (engine, request) = unsafe { (&*engine, CStr::from_ptr(request)) };
            match request.to_str() {
                Ok(text) => plan_json(engine, text),
                Err(e) => format!("{{\"error\":\"requête illisible : {e}\"}}"),
            }
        },
    );
    c_string(reply)
}

/// Frees a string returned by this library; null is accepted.
///
/// # Safety
/// `text` is null or a string returned by this library, not freed yet.
#[allow(unsafe_code)]
#[unsafe(no_mangle)]
pub unsafe extern "C" fn nemesis_string_free(text: *mut c_char) {
    if !text.is_null() {
        // SAFETY: the string was created by `CString::into_raw` here (contract above).
        drop(unsafe { CString::from_raw(text) });
    }
}

/// Closes an engine; null is accepted.
///
/// # Safety
/// `engine` is null or comes from `nemesis_engine_open`, not closed yet.
#[allow(unsafe_code)]
#[unsafe(no_mangle)]
pub unsafe extern "C" fn nemesis_engine_close(engine: *mut Engine) {
    if !engine.is_null() {
        // SAFETY: the engine was created by `Box::into_raw` here (contract above).
        drop(unsafe { Box::from_raw(engine) });
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn pack() -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../../data/fixtures_fictives/pack")
    }

    #[test]
    #[allow(unsafe_code)]
    fn plans_through_the_c_interface() {
        let dir = CString::new(pack().to_str().unwrap()).unwrap();
        let mut error = ptr::null_mut();
        // SAFETY: valid strings and pointers, freed below.
        unsafe {
            let engine = nemesis_engine_open(dir.as_ptr(), &raw mut error);
            assert!(!engine.is_null() && error.is_null());
            let request = CString::new(
                r#"{"from":"Gare des Flamboyants","to":"Embarcadère Sud","date":20261110,"time":27000}"#,
            )
            .unwrap();
            let reply = nemesis_engine_plan(engine, request.as_ptr());
            let text = CStr::from_ptr(reply).to_str().unwrap().to_owned();
            nemesis_string_free(reply);
            let info = nemesis_engine_info(engine);
            assert!(
                CStr::from_ptr(info)
                    .to_str()
                    .unwrap()
                    .contains("lagune-fictive")
            );
            nemesis_string_free(info);
            nemesis_engine_close(engine);
            let json: serde_json::Value = serde_json::from_str(&text).unwrap();
            let options = json["ok"]["options"].as_array().unwrap();
            assert!(options.len() >= 3, "{text}");
            assert_eq!(json["ok"]["is_fictional"], true);
        }
    }

    #[test]
    #[allow(unsafe_code)]
    fn errors_come_back_as_messages() {
        let dir = CString::new("/nulle/part").unwrap();
        let mut error = ptr::null_mut();
        // SAFETY: valid strings and pointers, freed below.
        unsafe {
            assert!(nemesis_engine_open(dir.as_ptr(), &raw mut error).is_null());
            assert!(!CStr::from_ptr(error).to_str().unwrap().is_empty());
            nemesis_string_free(error);
            let reply = nemesis_engine_plan(ptr::null(), ptr::null());
            assert!(CStr::from_ptr(reply).to_str().unwrap().contains("error"));
            nemesis_string_free(reply);
        }
        let engine = open(&pack()).unwrap();
        assert!(plan_json(&engine, "pas du json").contains("requête illisible"));
        assert!(
            plan_json(
                &engine,
                r#"{"from":"Nulle part","to":"x","date":20261110,"time":0}"#
            )
            .contains("error")
        );
    }
}
