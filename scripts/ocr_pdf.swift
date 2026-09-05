// OCR a scanned PDF using the macOS Vision framework.
//
// The district's union contracts are posted as page scans, so pypdf gets nothing out of
// them. Rather than add a Python OCR dependency, this uses what macOS already ships:
// PDFKit to rasterize each page and Vision's text recognizer to read it. No network, no
// third-party install, and the output lands next to the other extracted text.
//
//   swift scripts/ocr_pdf.swift <in.pdf> <out.txt> [scale] [--boxes]
//
// `--boxes` writes a TSV of every recognised line with its position and confidence
// instead of joined text. Reading order is enough for prose and useless for a table: six
// of the town's sixteen annual town reports are page scans, and their receipts and
// appropriations tables have columns that only exist as geometry. With boxes,
// `pdf_tables.layout_from_boxes()` rebuilds the same fixed-width form pypdf's layout mode
// produces for the digital reports, so one column algorithm serves both.
//
// Confidence travels with the text because an OCR digit is a reading, not a figure, and
// the caller has to be able to tell a 3 it is sure of from an 8 it guessed.

import Foundation
import PDFKit
import Vision
import CoreGraphics

let args = CommandLine.arguments
guard args.count >= 3, let doc = PDFDocument(url: URL(fileURLWithPath: args[1])) else {
    FileHandle.standardError.write("usage: ocr_pdf <in.pdf> <out.txt> [scale]\n".data(using: .utf8)!)
    exit(1)
}
let boxes = args.contains("--boxes")

// Which rotation to apply when rasterising, decided by measurement rather than by reading
// /Rotate.
//
// /Rotate does not say what PDFKit will do with the page, and the reports prove it: FY2011
// page 58 is marked /Rotate 90 and needs 90 degrees applied to come out upright, while
// FY2019 page 124 is marked /Rotate 270 and needs *none* -- PDFKit has already applied it.
// Reasoning from the spec gives the wrong answer for half the archive, and the failure is
// silent: Vision reads sideways text perfectly well and returns boxes that are tall and
// narrow, so every label in a column shares one y and the table collapses into one line of
// labels followed by one line of values.
//
// So each document is calibrated on a handful of its own pages: render at each of the four
// orientations, recognise, and keep the one that yields the most boxes wider than they are
// tall. Horizontal text in horizontal boxes is the only assumption, and it holds for every
// page in this archive.
func render(_ page: PDFPage, _ applied: Int, _ scale: Double) -> CGImage? {
    let b = page.bounds(for: .mediaBox)
    let sideways = (applied == 90 || applied == 270)
    let pw = sideways ? b.height : b.width, ph = sideways ? b.width : b.height
    guard let ctx = CGContext(data: nil, width: Int(pw * scale), height: Int(ph * scale),
                              bitsPerComponent: 8, bytesPerRow: 0,
                              space: CGColorSpaceCreateDeviceRGB(),
                              bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else {
        return nil
    }
    ctx.setFillColor(CGColor(gray: 1, alpha: 1))
    ctx.fill(CGRect(x: 0, y: 0, width: Int(pw * scale), height: Int(ph * scale)))
    ctx.scaleBy(x: CGFloat(scale), y: CGFloat(scale))
    switch applied {
    case 90:  ctx.translateBy(x: 0, y: b.width);            ctx.rotate(by: -.pi / 2)
    case 180: ctx.translateBy(x: b.width, y: b.height);     ctx.rotate(by: .pi)
    case 270: ctx.translateBy(x: b.height, y: 0);           ctx.rotate(by: .pi / 2)
    default: break
    }
    page.draw(with: .mediaBox, to: ctx)
    return ctx.makeImage()
}

func recognise(_ img: CGImage) -> [VNRecognizedTextObservation] {
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = true
    req.recognitionLanguages = ["en-US"]
    try? VNImageRequestHandler(cgImage: img, options: [:]).perform([req])
    return req.results ?? []
}

func wideFraction(_ obs: [VNRecognizedTextObservation]) -> Double {
    guard !obs.isEmpty else { return 0 }
    let wide = obs.filter { $0.boundingBox.width > $0.boundingBox.height }.count
    return Double(wide) / Double(obs.count)
}

// Calibrated PER PAGE, not per document, and on the *fraction* of horizontal boxes rather
// than the count.
//
// Both of those were learned the hard way. The FY2016 addendum turns out to mix
// orientations within one document -- page 1 needs no rotation applied and pages 2, 5, 9
// and 12 need 90 degrees -- so a single answer for the document is wrong for part of it.
// And counting horizontal boxes rather than taking their share rewards whichever
// orientation shatters the page into the most fragments: on that document the count picked
// 90 (338 boxes against 110) while the fraction picks correctly, 100% against 0%.
//
// Most pages are already upright, so 0 is tried first at low resolution and accepted when
// it is clearly right. Only the pages that fail pay for the other three.
// Does reading order run DOWN the page?
//
// Vision returns observations in reading order and recognises text at any orientation --
// it reads an upside-down page perfectly well and reports confidence 1.000 doing it. So
// neither the text nor the confidence separates upright from inverted, and box shape does
// not either: rotate a page 180 degrees and its lines are still wider than they are tall.
//
// What changes is the relationship between reading order and position. With the origin at
// bottom-left, an upright page has y DECREASING as the index rises; inverted, it
// increases. That correlation is the only signal that tells 0 from 180, or 90 from 270.
//
// Getting it wrong is not a small error. The FY2016 addendum was read a half-turn out,
// which reversed its row order AND its column order and dropped four rows -- every figure
// individually correct and the table unusable.
func readsDownward(_ obs: [VNRecognizedTextObservation]) -> Double {
    guard obs.count > 3 else { return 0 }
    let xs = (0..<obs.count).map(Double.init)
    let ys = obs.map { Double($0.boundingBox.midY) }
    let n = Double(obs.count)
    let mx = xs.reduce(0, +) / n, my = ys.reduce(0, +) / n
    var sxy = 0.0, sxx = 0.0, syy = 0.0
    for i in 0..<obs.count {
        let dx = xs[i] - mx, dy = ys[i] - my
        sxy += dx * dy; sxx += dx * dx; syy += dy * dy
    }
    if sxx == 0 || syy == 0 { return 0 }
    return sxy / (sxx * syy).squareRoot()
}

func orientation(_ page: PDFPage) -> Int {
    // Both tests are needed, and neither alone is enough.
    //
    // `wideFraction` separates upright-or-inverted from sideways. `readsDownward`
    // separates upright from inverted. An earlier version used only the first and had an
    // early exit that accepted 0 degrees whenever the boxes were wide -- which an
    // UPSIDE-DOWN page satisfies just as well, so a half-turn error could never be caught.
    // FY2011's payroll pages, scanned upside down, passed that test every time.
    var best = (applied: 0, score: -2.0)
    for applied in [0, 90, 180, 270] {
        guard let img = render(page, applied, 1.5) else { continue }
        let obs = recognise(img)
        guard obs.count > 3 else { continue }
        let wide = wideFraction(obs)
        if wide < 0.5 { continue }          // sideways; not a candidate
        // Reading order should run down the page, so the correlation should be negative.
        // Scored as its negation, and weighted by how horizontal the text is.
        let score = wide - readsDownward(obs)
        if score > best.score { best = (applied, score) }
    }
    return best.applied
}
let scaleArgs = args.dropFirst(3).filter { !$0.hasPrefix("--") }
let scale = Double(scaleArgs.first ?? "") ?? 2.0
var out = boxes ? "page\tx\ty\tw\th\tconf\ttext\n" : ""
var rotatedPages: [String] = []

for i in 0..<doc.pageCount {
    guard let page = doc.page(at: i) else { continue }
    let applied = orientation(page)
    guard let img = render(page, applied, scale) else { continue }
    if applied != 0 { rotatedPages.append("\(i + 1):\(applied)") }

    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = true
    req.recognitionLanguages = ["en-US"]
    try? VNImageRequestHandler(cgImage: img, options: [:]).perform([req])
    if boxes {
        // Vision's boundingBox is normalised with the origin at bottom-left. It is
        // emitted unchanged, in that coordinate space, so nothing downstream depends on
        // the raster scale this run happened to use.
        for obs in (req.results ?? []) {
            guard let cand = obs.topCandidates(1).first else { continue }
            let b = obs.boundingBox
            let text = cand.string.replacingOccurrences(of: "\t", with: " ")
            out += String(format: "%d\t%.5f\t%.5f\t%.5f\t%.5f\t%.3f\t",
                          i + 1, b.minX, b.minY, b.width, b.height, cand.confidence)
            out += text + "\n"
        }
    } else {
        let lines = (req.results ?? []).compactMap { $0.topCandidates(1).first?.string }
        out += "===PAGE \(i + 1)===\n" + lines.joined(separator: "\n") + "\n"
    }
    FileHandle.standardError.write("page \(i + 1)/\(doc.pageCount)\r".data(using: .utf8)!)
}
try out.write(toFile: args[2], atomically: true, encoding: .utf8)
FileHandle.standardError.write("\nwrote \(args[2]) (\(out.count) chars)\n".data(using: .utf8)!)
if !rotatedPages.isEmpty {
    FileHandle.standardError.write(
        "pages needing rotation: \(rotatedPages.joined(separator: " "))\n"
            .data(using: .utf8)!)
}
