// WORD-LEVEL boxes, because line-level boxes cannot see a column.
//
//   swift scripts/ocr_words.swift <in.pdf> <out.tsv> <firstPage> <lastPage> [scale]
//
// `ocr_pdf.swift --boxes` emits one row per Vision OBSERVATION, and a Vision observation
// is a LINE. On a page set in two columns that is fatal in a way no parser can undo: the
// annual report's personnel listing prints `FINANCE COMMITTEE (7 members)` in the left
// column and `GREEN COMMUNITIES COMMITTEE` in the right, Vision returns them as ONE
// observation, and its bounding box spans both columns. Measured on FY2022 page 9: 27
// observations for 27 printed lines, every x-centre between 0.495 and 0.500.
//
// So rule 13b's method -- measure the page, cluster on position -- had nothing to measure.
// Not because the page lacks the information but because the instrument threw it away
// before we saw it, which is rule 13's own shape: the thing that reformats before you look
// is part of the finding.
//
// Vision does keep it. `VNRecognizedText.boundingBox(for:)` returns a box for any
// character range inside the recognised string, so a box per WORD is available and it is
// what this writes. Same renderer as ocr_pdf.swift -- CGPDFPage, getBoxRect and
// drawPDFPage, with /Rotate folded into one transform -- because the diagnostic must not
// be built on a different view of the page from the extractor.
//
// One row per word: page, x, y, w, h, confidence, text. Same normalised bottom-left
// origin as the existing TSV, so anything that reads one can read the other.

import Foundation
import CoreGraphics
import PDFKit
import Vision

let args = CommandLine.arguments
guard args.count >= 5 else {
    FileHandle.standardError.write(
        "usage: ocr_words.swift <in.pdf> <out.tsv> <first> <last> [scale]\n"
            .data(using: .utf8)!)
    exit(2)
}
let scale = args.count > 5 ? (Double(args[5]) ?? 3.0) : 3.0
let first = Int(args[3]) ?? 1, last = Int(args[4]) ?? 1
guard let doc = PDFDocument(url: URL(fileURLWithPath: args[1])) else {
    FileHandle.standardError.write("cannot open \(args[1])\n".data(using: .utf8)!)
    exit(1)
}

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

var out = "page\tx\ty\tw\th\tconf\ttext\n"
var words = 0
var fallbacks = 0
for i in (first - 1)..<min(last, doc.pageCount) {
    guard let page = doc.page(at: i), let img = render(page, scale) else { continue }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    // LANGUAGE CORRECTION OFF. It helps a sentence and hurts a roster: these pages are
    // proper nouns, and a corrector that has never met `Bilotta-Simeone` will offer
    // something it has met. Names are the entire payload here.
    req.usesLanguageCorrection = false
    req.recognitionLanguages = ["en-US"]
    try? VNImageRequestHandler(cgImage: img, options: [:]).perform([req])

    for obs in (req.results ?? []) {
        guard let cand = obs.topCandidates(1).first else { continue }
        let s = cand.string
        // Split on whitespace and ask Vision where each piece sits. A range that Vision
        // declines to locate is skipped rather than guessed at.
        var idx = s.startIndex
        while idx < s.endIndex {
            if s[idx].isWhitespace { idx = s.index(after: idx); continue }
            var end = idx
            while end < s.endIndex && !s[end].isWhitespace { end = s.index(after: end) }
            let piece = String(s[idx..<end])
            // A WORD WHOSE BOX VISION WILL NOT GIVE IS STILL A WORD. The first version
            // wrote `if let box = try? cand.boundingBox(for:)` and dropped the word when
            // that failed -- silently, which is the shape of nearly every defect this
            // repo has found. It cost three consecutive lines on FY2022 page 8: Housing
            // Authority states five members and came back with NONE, while the existing
            // line-level TSV had all three names sitting there. A count that goes to zero
            // because the instrument declined to answer looks exactly like a board with
            // no members.
            //
            // So the observation's own box is the fallback, divided across the string by
            // character offset. That is an ESTIMATE of where the word sits and it is
            // marked as one: confidence is written negative so nothing downstream can
            // mistake a placed word for a measured one.
            var b: CGRect
            var measured = true
            if let box = try? cand.boundingBox(for: idx..<end) {
                b = box.boundingBox
            } else {
                measured = false
                let whole = obs.boundingBox
                let n = max(s.count, 1)
                let a0 = Double(s.distance(from: s.startIndex, to: idx)) / Double(n)
                let a1 = Double(s.distance(from: s.startIndex, to: end)) / Double(n)
                b = CGRect(x: whole.minX + whole.width * CGFloat(a0), y: whole.minY,
                           width: whole.width * CGFloat(a1 - a0), height: whole.height)
                fallbacks += 1
            }
            do {
                let flat = piece
                    .replacingOccurrences(of: "\t", with: " ")
                    .replacingOccurrences(of: "\n", with: " ")
                    .replacingOccurrences(of: "\r", with: " ")
                out += String(format: "%d\t%.5f\t%.5f\t%.5f\t%.5f\t%.3f\t%@\n",
                              i + 1, b.minX, b.minY, b.width, b.height,
                              measured ? cand.confidence : -cand.confidence, flat)
                words += 1
            }
            idx = end
        }
    }
    FileHandle.standardError.write("page \(i + 1)\r".data(using: .utf8)!)
}
try out.write(toFile: args[2], atomically: true, encoding: .utf8)
FileHandle.standardError.write(
    "\nwrote \(args[2]): \(words) words, \(fallbacks) placed from the line box\n"
        .data(using: .utf8)!)
