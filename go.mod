module tlk

go 1.26.2

// v1.4.0+ requires Hugo >= 0.156.0 extended. Its only change over v1.3.0 is
// swapping the deprecated Image.Exif for Image.Meta, which this site does not
// use, so it stays pinned until the Hugo version moves.
require github.com/mfg92/hugo-shortcode-gallery v1.3.0 // indirect
