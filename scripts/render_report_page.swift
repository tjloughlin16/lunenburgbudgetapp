// Render pages of a PDF to PNG, so a table can be READ rather than OCR'd.
//
//   swift scripts/render_report_page.swift <in.pdf> <out-dir> <page> [page...] [--scale N]
//
// WHY THIS EXISTS ALONGSIDE ocr_pdf.swift
//
// `ocr_pdf.swift` runs macOS Vision over a page and returns text with geometry. That is the
// right instrument for most of this archive and it is 99% accurate on the special revenue
// schedule -- which is not good enough, because a schedule either ties to its own printed
// GRAND TOTAL or it does not. On FY2022 it dropped one cell out of seventy on page 33, read
// one digit wrong on page 34, and misread the printed total it was being checked against.
//
// The pages themselves are clean. So this renders them for direct reading, and the
// transcription is checked against the report's own printed total plus the identity the
// table states. See scripts/verify_special_revenue_read.py.
//
// Page numbers are the PRINTED page number, which is what every catalogue in this
// repository uses. The offset to the PDF's own index is worked out from the document and
// reported, rather than assumed -- they differ by a cover offset that is not constant
// across the sixteen annual reports.
import Foundation
import PDFKit
import CoreGraphics
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count >= 4, let doc = PDFDocument(url: URL(fileURLWithPath: args[1])) else {
    FileHandle.standardError.write(
        "usage: render_report_page <in.pdf> <out-dir> <page>... [--scale N]\n".data(using: .utf8)!)
    exit(1)
}
let outDir = args[2]
var scale = 2.0
if let i = args.firstIndex(of: "--scale"), i + 1 < args.count { scale = Double(args[i+1]) ?? 2.0 }
let pages = args.dropFirst(3).compactMap { Int($0) }

// The offset between the printed page number and the PDF index, found by looking for a
// page whose own text is just its number.
var offset = 1
for idx in 0..<min(doc.pageCount, 60) {
    guard let t = doc.page(at: idx)?.string?.trimmingCharacters(in: .whitespacesAndNewlines)
    else { continue }
    if let n = Int(t), n > 1 { offset = idx - n + 1; break }
}
FileHandle.standardError.write("printed page + \(offset) = pdf index\n".data(using: .utf8)!)

try? FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true)
for printed in pages {
    guard let page = doc.page(at: printed + offset - 1) else { continue }
    // ROTATION IS NOT OPTIONAL TO HANDLE, and getting it wrong is silent.
    //
    // `bounds(for:)` returns the box BEFORE rotation, while `draw(with:to:)` applies it.
    // Six of the sixteen annual reports are scanned landscape and carry /Rotate 270, so a
    // canvas sized from the unrotated box clipped the top third of every FY2021 page --
    // and the result still looked like a valid page of the table, just starting partway
    // down. Nothing about it said "cropped".
    var r = page.bounds(for: .mediaBox)
    if page.rotation == 90 || page.rotation == 270 {
        r = CGRect(x: 0, y: 0, width: r.height, height: r.width)
    }
    guard let ctx = CGContext(data: nil, width: Int(r.width * scale), height: Int(r.height * scale),
        bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(),
        bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { continue }
    ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
    ctx.fill(CGRect(x: 0, y: 0, width: Int(r.width * scale), height: Int(r.height * scale)))
    ctx.scaleBy(x: CGFloat(scale), y: CGFloat(scale))
    page.draw(with: .mediaBox, to: ctx)
    guard let img = ctx.makeImage() else { continue }
    let url = URL(fileURLWithPath: "\(outDir)/page\(printed).png")
    guard let dest = CGImageDestinationCreateWithURL(
        url as CFURL, UTType.png.identifier as CFString, 1, nil) else { continue }
    CGImageDestinationAddImage(dest, img, nil)
    CGImageDestinationFinalize(dest)
    print("page\(printed).png")
}
