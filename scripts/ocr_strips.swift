// Render PDF pages to PNG, and read a PNG with Vision at BOTH recognition levels.
//
//   ocr_strips render <in.pdf> <first> <last> <scale> <outdir>   -> <outdir>/p<N>.png
//   ocr_strips ocr <a.png> [<b.png> ...]          -> <a.png>.acc.tsv and <a.png>.fast.tsv
//
// WHY BOTH LEVELS. The town's GROSS WAGES pages are a plain six-column table (surname,
// given name, amount, twice), and Vision's ACCURATE level, handed one, returns a fraction of
// it: measured on FY2024 pdf page 188, 100 observations for 282 printed cells, and on FY2023
// page 191, 26 of about 282. The FAST level returns 282 and 283 on the same two images.
// Neither level is better everywhere -- FY2019 page 199 reads 274 accurate and 254 fast --
// so the caller (scripts/extract_teacher_pay.py) reads both and keeps, cell by cell, the
// reading it can check. The page is clean either way; the instrument is what fails, which
// is rule 13c: a reader that finds nothing is a statement about the reader.
//
// The renderer is the same CGPDFPage transform as ocr_words.swift, so a digital page and a
// scanned one go through one path.
//
// Output, one row per observation: x (left), y (centre), w, h, confidence, text --
// normalised to the image, bottom-left origin.

import Foundation
import CoreGraphics
import ImageIO
import PDFKit
import UniformTypeIdentifiers
import Vision

func render(_ page: PDFPage, _ scale: Double) -> CGImage? {
    guard let ref = page.pageRef else { return nil }
    let raw = ref.getBoxRect(.mediaBox)
    let spin = ((Int(ref.rotationAngle)) % 360 + 360) % 360
    let sideways = (spin == 90 || spin == 270)
    let pw = sideways ? raw.height : raw.width
    let ph = sideways ? raw.width : raw.height
    guard let ctx = CGContext(data: nil, width: Int(pw * scale), height: Int(ph * scale),
                              bitsPerComponent: 8, bytesPerRow: 0,
                              space: CGColorSpaceCreateDeviceRGB(),
                              bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else {
        return nil
    }
    ctx.setFillColor(CGColor(gray: 1, alpha: 1))
    ctx.fill(CGRect(x: 0, y: 0, width: Int(pw * scale), height: Int(ph * scale)))
    ctx.scaleBy(x: CGFloat(scale), y: CGFloat(scale))
    switch spin {
    case 90:  ctx.translateBy(x: 0, y: raw.width);           ctx.rotate(by: -CGFloat.pi / 2)
    case 180: ctx.translateBy(x: raw.width, y: raw.height);  ctx.rotate(by: CGFloat.pi)
    case 270: ctx.translateBy(x: raw.height, y: 0);          ctx.rotate(by: CGFloat.pi / 2)
    default: break
    }
    ctx.translateBy(x: -raw.origin.x, y: -raw.origin.y)
    ctx.drawPDFPage(ref)
    return ctx.makeImage()
}

let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("usage: ocr_strips render|ocr ...\n".data(using: .utf8)!)
    exit(2)
}
if args[1] == "render" {
    guard args.count == 7, let doc = PDFDocument(url: URL(fileURLWithPath: args[2])) else {
        FileHandle.standardError.write("cannot open \(args[2])\n".data(using: .utf8)!)
        exit(1)
    }
    let first = Int(args[3]) ?? 1, last = Int(args[4]) ?? 1, scale = Double(args[5]) ?? 3.0
    for i in (first - 1)..<min(last, doc.pageCount) {
        guard let page = doc.page(at: i), let img = render(page, scale) else { continue }
        let url = URL(fileURLWithPath: "\(args[6])/p\(i + 1).png")
        guard let dest = CGImageDestinationCreateWithURL(url as CFURL,
                                                         UTType.png.identifier as CFString,
                                                         1, nil) else { exit(1) }
        CGImageDestinationAddImage(dest, img, nil)
        CGImageDestinationFinalize(dest)
    }
    exit(0)
}
for path in args.dropFirst(2) {
    for (suffix, level) in [("acc", VNRequestTextRecognitionLevel.accurate),
                            ("fast", VNRequestTextRecognitionLevel.fast)] {
        let req = VNRecognizeTextRequest()
        req.recognitionLevel = level
        // Language correction off: the payload is proper nouns (see ocr_words.swift).
        req.usesLanguageCorrection = false
        req.recognitionLanguages = ["en-US"]
        try VNImageRequestHandler(url: URL(fileURLWithPath: path), options: [:]).perform([req])
        var out = "x\ty\tw\th\tconf\ttext\n"
        for o in req.results ?? [] {
            guard let c = o.topCandidates(1).first else { continue }
            let b = o.boundingBox
            let t = c.string.replacingOccurrences(of: "\t", with: " ")
            out += String(format: "%.5f\t%.5f\t%.5f\t%.5f\t%.3f\t", b.minX, b.midY, b.width,
                          b.height, c.confidence) + t + "\n"
        }
        try out.write(toFile: path + "." + suffix + ".tsv", atomically: true, encoding: .utf8)
    }
}
