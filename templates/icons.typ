// FALLBACK — committed, empty on purpose. This repo ships NO third-party
// icon artwork: `scripts/harvest_icons.py <cv folder>` fetches the path data
// into an `icons.typ` beside the deliverable's `lib.typ` copy at build time.
// This file is what `#import "icons.typ": *` resolves to when nothing was
// fetched (no network, no script run): every mark is empty, `pmark` draws
// nothing, and the contact line keeps its URLs in plain text. The import
// therefore never fails. Do not fill it in — a harvest writes the CV folder,
// never this file.

#let li-body = ""
#let li-vb = ""
#let gh-body = ""
#let gh-vb = ""
#let mail-body = ""
#let mail-vb = ""
#let web-body = ""
#let web-vb = ""
#let phone-body = ""
#let phone-vb = ""
#let pin-body = ""
#let pin-vb = ""
#let ph-envelope_simple_fill-body = ""
#let ph-envelope_simple_fill-vb = ""
#let ph-globe_fill-body = ""
#let ph-globe_fill-vb = ""
#let ph-phone_fill-body = ""
#let ph-phone_fill-vb = ""
#let ph-map_pin_fill-body = ""
#let ph-map_pin_fill-vb = ""
#let bi-envelope_fill-body = ""
#let bi-envelope_fill-vb = ""
#let bi-globe-body = ""
#let bi-globe-vb = ""
#let bi-telephone_fill-body = ""
#let bi-telephone_fill-vb = ""
#let bi-geo_alt_fill-body = ""
#let bi-geo_alt_fill-vb = ""
