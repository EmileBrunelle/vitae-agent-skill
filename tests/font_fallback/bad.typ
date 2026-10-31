// Font fallback fixture, positive: the requested family does not draw Latin (here: it is not installed at all,
// the PDF looks the same as a family whose files lack the basic Latin range, e.g. fontsource latin-ext).
#set page(width: 21cm, height: 29.7cm, margin: 2cm)
#set text(font: "Vitae Nonexistent Sans", size: 11pt)
= Jane Roe
Backend developer. Built a billing service in Go, cut p95 latency from 480 ms to 120 ms across 12 endpoints.
