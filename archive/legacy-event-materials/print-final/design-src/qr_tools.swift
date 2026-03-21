import AppKit
import CoreImage
import Foundation
import Vision

enum QRToolError: Error {
    case invalidArguments
    case encodingFailed
    case decodingFailed
}

func encodeQRCode(_ text: String, outputPath: String) throws {
    guard let data = text.data(using: .utf8) else {
        throw QRToolError.encodingFailed
    }

    guard let filter = CIFilter(name: "CIQRCodeGenerator") else {
        throw QRToolError.encodingFailed
    }
    filter.setValue(data, forKey: "inputMessage")
    filter.setValue("M", forKey: "inputCorrectionLevel")

    guard let outputImage = filter.outputImage else {
        throw QRToolError.encodingFailed
    }

    let transform = CGAffineTransform(scaleX: 24, y: 24)
    let scaled = outputImage.transformed(by: transform)
    let rep = NSCIImageRep(ciImage: scaled)
    let qrSize = rep.size
    let padding = max(qrSize.width * 0.12, 36)
    let finalSize = NSSize(width: qrSize.width + padding * 2, height: qrSize.height + padding * 2)

    let image = NSImage(size: finalSize)
    image.lockFocus()
    if let context = NSGraphicsContext.current {
        context.imageInterpolation = .none
    }
    NSColor.white.setFill()
    NSBezierPath(rect: NSRect(origin: .zero, size: finalSize)).fill()
    rep.draw(in: NSRect(x: padding, y: padding, width: qrSize.width, height: qrSize.height))
    image.unlockFocus()

    guard
        let tiff = image.tiffRepresentation,
        let bitmap = NSBitmapImageRep(data: tiff),
        let pngData = bitmap.representation(using: .png, properties: [:])
    else {
        throw QRToolError.encodingFailed
    }

    try pngData.write(to: URL(fileURLWithPath: outputPath))
}

func decodeQRCode(_ imagePath: String) throws -> String {
    let request = VNDetectBarcodesRequest()
    request.symbologies = [.qr]
    let handler = VNImageRequestHandler(url: URL(fileURLWithPath: imagePath), options: [:])
    try handler.perform([request])
    guard let payload = request.results?.first?.payloadStringValue else {
        throw QRToolError.decodingFailed
    }
    return payload
}

let args = CommandLine.arguments
guard args.count >= 2 else {
    throw QRToolError.invalidArguments
}

switch args[1] {
case "encode":
    guard args.count == 4 else {
        throw QRToolError.invalidArguments
    }
    try encodeQRCode(args[2], outputPath: args[3])
case "decode":
    guard args.count == 3 else {
        throw QRToolError.invalidArguments
    }
    print(try decodeQRCode(args[2]))
default:
    throw QRToolError.invalidArguments
}
