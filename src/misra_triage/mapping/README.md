# mapping

Longest-prefix path matching to attach SWC ownership, ASIL, and DOORS IDs.

`ViolationEnricher` reads:

- `config/owner_map.yaml` — `prefix` → `swc`, `owner`, `asil`  
- `config/doors_map.yaml` — `prefix` → `doors_id`  

Rules are sorted by prefix length (longest wins). Unmatched paths use `default_owner`.
