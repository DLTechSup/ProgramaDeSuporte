/// Locks the UI/behavior to one role, chosen at compile time:
/// `informax-client` (customer machine) only receives connections,
/// `informax-tech` (technician) only starts them.
pub fn apply_edition() {
    #[cfg(any(feature = "informax-client", feature = "informax-tech"))]
    {
        let conn_type = if cfg!(feature = "informax-client") {
            "incoming"
        } else {
            "outgoing"
        };
        if let Ok(mut settings) = hbb_common::config::HARD_SETTINGS.write() {
            settings.insert("conn-type".to_owned(), conn_type.to_owned());
        }
    }
}

/// Fixes the server and public key at build time (`INFORMAX_SERVER` / `INFORMAX_KEY`),
/// so every installed copy uses the company's own server instead of the public one.
pub fn apply_server() {
    let mut options = Vec::new();
    if let Some(server) = option_env!("INFORMAX_SERVER").filter(|s| !s.is_empty()) {
        options.push(("custom-rendezvous-server", server));
    }
    if let Some(key) = option_env!("INFORMAX_KEY").filter(|s| !s.is_empty()) {
        options.push(("key", key));
    }
    if options.is_empty() {
        return;
    }
    if let Ok(mut settings) = hbb_common::config::OVERWRITE_SETTINGS.write() {
        for (k, v) in options {
            settings.insert(k.to_owned(), v.to_owned());
        }
    }
}
