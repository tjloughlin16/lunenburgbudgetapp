// Render one page of a PDF to PNG, upright, for reading with human or model eyes.
//
// This exists because of what verification actually requires here. Most tables in the
// annual town reports print no total, so there is no arithmetic that can prove an
// extraction complete. What CAN prove it is the page itself: render it, read it, and
// compare it to what was extracted. Rule 13 says to check what a reader sees rather than
// only what the file holds — this is the instrument for doing that.
//
// Orientation is calibrated per page, the same way `ocr_pdf.swift` does it, because
// /Rotate does not say what the renderer will do and orientation varies within a single
// document.
//
//   swift scripts/render_page.swift <in.pdf> <page> <out.png> [scale] [x y w h]
//
// The optional normalised crop (origin top-left) narrows to part of a page when a table
// occupies only a corner of it.

import Foundation
import PDFKit
import Vision
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

let a = CommandLine.arguments
guard a.count >= 4, let doc = PDFDocument(url: URL(fileURLWithPath: a[1])),
      let pageNo = Int(a[2]), let page = doc.page(at: pageNo - 1) else {
    FileHandle.standardError.write(
        "usage: render_page <in.pdf> <page> <out.png> [scale] [x y w h]\n".data(using: .utf8)!)
    exit(1)
}
let scale = a.count > 4 ? (Double(a[4]) ?? 3.0) : 3.0

func render(_ applied: Int, _ s: Double) -> CGImage? {
    let b = page.bounds(for: .mediaBox)
    let sideways = (applied == 90 || applied == 270)
    let pw = sideways ? b.height : b.width, ph = sideways ? b.width : b.height
    guard let ctx = CGContext(data: nil, width: Int(pw * s), height: Int(ph * s),
                              bitsPerComponent: 8, bytesPerRow: 0,
                              space: CGColorSpaceCreateDeviceRGB(),
                              bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { return nil }
    ctx.setFillColor(CGColor(gray: 1, alpha: 1))
    ctx.fill(CGRect(x: 0, y: 0, width: Int(pw * s), height: Int(ph * s)))
    ctx.scaleBy(x: CGFloat(s), y: CGFloat(s))
    switch applied {
    case 90:  ctx.translateBy(x: 0, y: b.width);        ctx.rotate(by: -.pi / 2)
    case 180: ctx.translateBy(x: b.width, y: b.height); ctx.rotate(by: .pi)
    case 270: ctx.translateBy(x: b.height, y: 0);       ctx.rotate(by: .pi / 2)
    default: break
    }
    page.draw(with: .mediaBox, to: ctx)
    return ctx.makeImage()
}

// Pick the orientation whose recognised text is mostly wider than it is tall.
func upright() -> Int {
    var best = (applied: 0, score: -1.0)
    for applied in [0, 90, 180, 270] {
        guard let img = render(applied, 1.5) else { continue }
        let req = VNRecognizeTextRequest()
        req.recognitionLevel = .fast
        try? VNImageRequestHandler(cgImage: img, options: [:]).perform([req])
        let obs = req.results ?? []
        guard !obs.isEmpty else { continue }
        let wide = obs.filter { $0.boundingBox.width > $0.boundingBox.height }.count
        let score = Double(wide) / Double(obs.count) * Double(min(obs.count, 200))
        if score > best.score { best = (applied, score) }
    }
    return best.applied
}

guard var img = render(upright(), scale) else { exit(1) }

if a.count >= 9, let nx = Double(a[5]), let ny = Double(a[6]),
   let nw = Double(a[7]), let nh = Double(a[8]) {
    let W = Double(img.width), H = Double(img.height)
    if let c = img.cropping(to: CGRect(x: nx * W, y: ny * H, width: nw * W, height: nh * H)) {
        img = c
    }
}

guard let dst = CGImageDestinationCreateWithURL(
        URL(fileURLWithPath: a[3]) as CFURL, UTType.png.identifier as CFString, 1, nil) else {
    exit(1)
}
CGImageDestinationAddImage(dst, img, nil)
CGImageDestinationFinalize(dst)
FileHandle.standardError.write("wrote \(a[3]) (\(img.width)x\(img.height))\n".data(using: .utf8)!)
