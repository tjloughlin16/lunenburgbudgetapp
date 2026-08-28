// OCR a scanned PDF using the macOS Vision framework.
//
// The district's union contracts are posted as page scans, so pypdf gets nothing out of
// them. Rather than add a Python OCR dependency, this uses what macOS already ships:
// PDFKit to rasterize each page and Vision's text recognizer to read it. No network, no
// third-party install, and the output lands next to the other extracted text.
//
//   swift scripts/ocr_pdf.swift <in.pdf> <out.txt> [scale]

import Foundation
import PDFKit
import Vision
import CoreGraphics

let args = CommandLine.arguments
guard args.count >= 3, let doc = PDFDocument(url: URL(fileURLWithPath: args[1])) else {
    FileHandle.standardError.write("usage: ocr_pdf <in.pdf> <out.txt> [scale]\n".data(using: .utf8)!)
    exit(1)
}
let scale = args.count > 3 ? (Double(args[3]) ?? 2.0) : 2.0
var out = ""

for i in 0..<doc.pageCount {
    guard let page = doc.page(at: i) else { continue }
    let bounds = page.bounds(for: .mediaBox)
    let w = Int(bounds.width * scale), h = Int(bounds.height * scale)
    guard let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8,
                              bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(),
                              bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { continue }
    ctx.setFillColor(CGColor(gray: 1, alpha: 1))
    ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
    ctx.scaleBy(x: CGFloat(scale), y: CGFloat(scale))
    page.draw(with: .mediaBox, to: ctx)
    guard let img = ctx.makeImage() else { continue }

    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = true
    req.recognitionLanguages = ["en-US"]
    try? VNImageRequestHandler(cgImage: img, options: [:]).perform([req])
    let lines = (req.results ?? []).compactMap { $0.topCandidates(1).first?.string }
    out += "===PAGE \(i + 1)===\n" + lines.joined(separator: "\n") + "\n"
    FileHandle.standardError.write("page \(i + 1)/\(doc.pageCount)\r".data(using: .utf8)!)
}
try out.write(toFile: args[2], atomically: true, encoding: .utf8)
FileHandle.standardError.write("\nwrote \(args[2]) (\(out.count) chars)\n".data(using: .utf8)!)
