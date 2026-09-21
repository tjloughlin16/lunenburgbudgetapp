// Render one page of a PDF to a PNG, so it can be LOOKED at.
//
//   swift scripts/render_pdf_page.swift <in.pdf> <page> <out.png>
//
// Step 4 of notes/process/INGESTING-A-TABLE-FAMILY.md, and the one that settles
// things no amount of inference does. In a single day it found: a rotated page
// clipping 20% of every landscape document, a `4` scanned as a `1` that left a
// column $3 short, and three years of a fund that had just been reported missing
// and registered as a gap.
//
// It uses CGPDFPage rather than PDFKit deliberately: getBoxRect and drawPDFPage
// agree with each other about what the page is, where PDFPage.bounds(for:) applies
// /Rotate and PDFPage.draw(with:to:) does not. That disagreement is the clipping
// bug, so the diagnostic must not be built on the thing it is diagnosing.

import Foundation
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers
let url = URL(fileURLWithPath: CommandLine.arguments[1])
let pageNo = Int(CommandLine.arguments[2])!
let out = URL(fileURLWithPath: CommandLine.arguments[3])
guard let doc = CGPDFDocument(url as CFURL), let page = doc.page(at: pageNo) else { exit(1) }
let r = page.getBoxRect(.mediaBox)
let s: CGFloat = 2.0
let ctx = CGContext(data: nil, width: Int(r.width*s), height: Int(r.height*s),
                    bitsPerComponent: 8, bytesPerRow: 0,
                    space: CGColorSpaceCreateDeviceRGB(),
                    bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
ctx.setFillColor(CGColor(red:1,green:1,blue:1,alpha:1))
ctx.fill(CGRect(x:0,y:0,width:r.width*s,height:r.height*s))
ctx.scaleBy(x:s,y:s)
ctx.drawPDFPage(page)
let img = ctx.makeImage()!
let dest = CGImageDestinationCreateWithURL(out as CFURL, UTType.png.identifier as CFString, 1, nil)!
CGImageDestinationAddImage(dest, img, nil)
CGImageDestinationFinalize(dest)
print("wrote \(out.path)  mediaBox \(r)")
