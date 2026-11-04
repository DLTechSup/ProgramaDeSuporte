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
