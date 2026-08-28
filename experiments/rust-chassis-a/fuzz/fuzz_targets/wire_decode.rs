#![no_main]

use libfuzzer_sys::fuzz_target;
use metao_wire::{decode_request, decode_response};

fuzz_target!(|data: &[u8]| {
    if let Ok(text) = std::str::from_utf8(data) {
        let _ = decode_request(text);
        let _ = decode_response(text);
    }
});
