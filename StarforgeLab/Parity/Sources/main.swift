import Foundation
import StarforgeCore
import StarforgeEngine

@main
struct StarforgeLabParity {
    static func main() async throws {
        let resources = try bundleResources()
        let appOutput = temporaryDirectory("starforge-app")
        let refOutput = temporaryDirectory("starforge-ref")
        defer {
            try? FileManager.default.removeItem(at: appOutput)
            try? FileManager.default.removeItem(at: refOutput)
        }

        let request = RenderRequest()
        let service = RenderService()
        var appManifest: Manifest?

        for try await event in await service.run(request, into: appOutput) {
            switch event {
            case .manifestReady(let manifest):
                appManifest = manifest
            case .failed(let error):
                throw CheckFailure("app render failed: \(error.localizedDescription)")
            default:
                break
            }
        }

        guard let appManifest else {
            throw CheckFailure("app render did not produce a manifest")
        }

        try runBundledCLI(resources: resources, output: refOutput, request: request)
        let refManifest = try Manifest.decode(from: Data(contentsOf: refOutput.appendingPathComponent("manifest.json")))

        let appGenome = try normalizedJSONObject(appManifest.selectedGenome)
        let refGenome = try normalizedJSONObject(refManifest.selectedGenome)
        try check(appGenome == refGenome, "selected_genome differs between app service and bundled CLI")

        let appPoster = appOutput.appendingPathComponent("starforge_poster.png")
        let refPoster = refOutput.appendingPathComponent("starforge_poster.png")
        let appHash = try sha256(appPoster)
        let refHash = try sha256(refPoster)
        try check(appHash == refHash, "poster bytes differ between app service and bundled CLI")

        print("environment_signature=\(try environmentSignature(resources: resources))")
        print("poster_sha256=\(appHash)")
        print("selected_genome=match")
        print("parity=pass")
    }

    private static func bundleResources() throws -> URL {
        guard let path = ProcessInfo.processInfo.environment["STARFORGE_BUNDLE_RESOURCES"], !path.isEmpty else {
            throw CheckFailure("STARFORGE_BUNDLE_RESOURCES is required")
        }
        return URL(fileURLWithPath: path)
    }

    private static func temporaryDirectory(_ prefix: String) -> URL {
        FileManager.default.temporaryDirectory
            .appendingPathComponent("\(prefix)-\(UUID().uuidString)", isDirectory: true)
    }

    private static func runBundledCLI(resources: URL, output: URL, request: RenderRequest) throws {
        let locations = try EngineLocator.locate()
        let process = Process()
        process.executableURL = locations.executableURL
        process.arguments = locations.leadingArguments + (try ArgumentBuilder.arguments(for: request, outputDirectory: output))
        process.currentDirectoryURL = locations.engineRoot
        process.environment = locations.environment
        let stderr = Pipe()
        process.standardError = stderr
        try process.run()
        process.waitUntilExit()
        if process.terminationStatus != 0 {
            let data = stderr.fileHandleForReading.readDataToEndOfFile()
            let message = String(data: data, encoding: .utf8) ?? "unknown error"
            throw CheckFailure("bundled CLI failed: \(message)")
        }
    }

    private static func normalizedJSONObject<T: Encodable>(_ value: T) throws -> NSDictionary {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        let data = try encoder.encode(value)
        guard let object = try JSONSerialization.jsonObject(with: data) as? NSDictionary else {
            throw CheckFailure("could not normalize JSON object")
        }
        return object
    }

    private static func sha256(_ url: URL) throws -> String {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/shasum")
        process.arguments = ["-a", "256", url.path]
        let stdout = Pipe()
        process.standardOutput = stdout
        try process.run()
        process.waitUntilExit()
        if process.terminationStatus != 0 {
            throw CheckFailure("shasum failed for \(url.path)")
        }
        let data = stdout.fileHandleForReading.readDataToEndOfFile()
        let text = String(data: data, encoding: .utf8) ?? ""
        return text.split(separator: " ").first.map(String.init) ?? ""
    }

    private static func environmentSignature(resources: URL) throws -> String {
        let code = """
import platform, numpy, PIL
print(f"{platform.system()}-{platform.machine()}-py{platform.python_version_tuple()[0]}.{platform.python_version_tuple()[1]}-numpy{numpy.__version__}-pillow{PIL.__version__}")
"""
        let locations = try EngineLocator.locate()
        let process = Process()
        process.executableURL = locations.executableURL
        process.arguments = locations.leadingArguments + ["-c", code]
        process.currentDirectoryURL = locations.engineRoot
        process.environment = locations.environment
        let stdout = Pipe()
        let stderr = Pipe()
        process.standardOutput = stdout
        process.standardError = stderr
        try process.run()
        process.waitUntilExit()
        if process.terminationStatus != 0 {
            let data = stderr.fileHandleForReading.readDataToEndOfFile()
            let message = String(data: data, encoding: .utf8) ?? "unknown error"
            throw CheckFailure("environment signature failed: \(message)")
        }
        let data = stdout.fileHandleForReading.readDataToEndOfFile()
        return (String(data: data, encoding: .utf8) ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func check(_ condition: Bool, _ message: String) throws {
        if !condition {
            throw CheckFailure(message)
        }
    }
}

private struct CheckFailure: Error, CustomStringConvertible {
    let description: String

    init(_ description: String) {
        self.description = description
    }
}
