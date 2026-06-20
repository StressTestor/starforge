import Foundation
import StarforgeCore
import StarforgeEngine

@main
struct StarforgeLabChecks {
    static func main() throws {
        try testCommittedFixturesDecode()
        try testPlainRenderManifestDecodesAndRoundTripsNullSeedScore()
        try testEverythingOnManifestDecodesDynamicReasonKeysAndStudioRows()
        try testStudioCuratorStudioRowsDecode()
        try testRenderRequestValidatesPythonBoundsBeforeProcessLaunch()
        try testBuildsArgvForRealStarforgeCliWithoutShellQuoting()
        try testRejectsDoomedRequestsBeforeProcessLaunch()
        print("StarforgeLabChecks passed")
    }

    private static func testCommittedFixturesDecode() throws {
        for fixture in ["plain_manifest", "full_manifest", "studio_curator_manifest"] {
            let data = try Data(contentsOf: checkoutRoot().appendingPathComponent("StarforgeLab/Checks/Fixtures/\(fixture).json"))
            let manifest = try Manifest.decode(from: data)
            try check(manifest.version == packageVersion(), "\(fixture) version follows vendored package")
            try assertJSONRoundTrips(manifest, original: data)
        }

        let studioCurator = try Manifest.decode(
            from: Data(contentsOf: checkoutRoot().appendingPathComponent("StarforgeLab/Checks/Fixtures/studio_curator_manifest.json"))
        )
        try check(studioCurator.curator == "studio", "studio-curator fixture decoded")
        try check(!studioCurator.studio.isEmpty, "studio-curator fixture includes studio rows")
        try check(studioCurator.collection.contains { $0.score.reasons.keys.contains("subject_focus") }, "studio curator reason keys decoded from fixture")
    }

    private static func testPlainRenderManifestDecodesAndRoundTripsNullSeedScore() throws {
        let data = try renderManifest(arguments: [
            "--width", "96",
            "--height", "96",
            "--frames", "2"
        ])

        let manifest = try Manifest.decode(from: data)

        try check(manifest.project == "starforge-lab", "project sentinel decoded")
        try check(manifest.version == packageVersion(), "manifest version follows vendored package")
        try check(manifest.seedCandidates.count == 1, "plain seed candidate fallback decoded")
        try check(manifest.seedCandidates[0].score == nil, "plain seed score remains nil")
        try check(manifest.seedCandidates[0].reasons == nil, "plain seed reasons remain absent")
        try assertJSONRoundTrips(manifest, original: data)
    }

    private static func testEverythingOnManifestDecodesDynamicReasonKeysAndStudioRows() throws {
        let data = try renderManifest(arguments: [
            "--width", "96",
            "--height", "96",
            "--frames", "2",
            "--seed-gallery", "2",
            "--batch", "2",
            "--top-k", "2",
            "--studio",
            "--cross-subject",
            "--scale-preview"
        ])

        let manifest = try Manifest.decode(from: data)

        try check(manifest.collection.count == 2, "collection entries decoded")
        try check(!manifest.collection[0].score.reasons.isEmpty, "dynamic score reasons decoded")
        try check(!manifest.studio.isEmpty, "studio rows decoded")
        try check(manifest.video.mp4 == "not requested", "video status decoded")
        try check(manifest.selectedGenome.subject == manifest.selectedSubject, "selected genome subject decoded")
        try assertJSONRoundTrips(manifest, original: data)
    }

    private static func testStudioCuratorStudioRowsDecode() throws {
        let data = try renderManifest(arguments: [
            "--width", "96",
            "--height", "96",
            "--frames", "2",
            "--batch", "2",
            "--top-k", "2",
            "--studio",
            "--curator", "studio"
        ])

        let manifest = try Manifest.decode(from: data)
        try check(manifest.curator == "studio", "studio curator decoded")
        try check(manifest.collection.contains { $0.score.reasons.keys.contains("subject_focus") }, "studio reason keys decoded")
        try check(!manifest.studio.isEmpty, "studio-curator studio rows decoded")
        try assertJSONRoundTrips(manifest, original: data)
    }

    private static func testRenderRequestValidatesPythonBoundsBeforeProcessLaunch() throws {
        var request = RenderRequest()
        request.width = 63
        try checkThrowsValidation(try request.validated(), "width lower bound")

        request.width = 1600
        request.curator = "bogus"
        try checkThrowsValidation(try request.validated(), "curator membership")
    }

    private static func testBuildsArgvForRealStarforgeCliWithoutShellQuoting() throws {
        var request = RenderRequest()
        request.width = 1200
        request.height = 900
        request.frames = 12
        request.seed = 42
        request.preset = "deep-field"
        request.subject = "wormhole"
        request.seedGallery = 3
        request.batch = 4
        request.topK = 2
        request.crossSubject = true
        request.studio = true
        request.video = true
        request.scalePreview = true
        request.curator = "studio"
        request.supersample = 2

        let output = URL(fileURLWithPath: "/tmp/starforge-lab-test")
        let arguments = try ArgumentBuilder.arguments(for: request, outputDirectory: output)

        try check(Array(arguments.prefix(4)) == ["-m", "starforge.cli", "--output", output.path], "argv starts with module invocation")
        try check(arguments.contains("--cross-subject"), "cross-subject flag present")
        try check(arguments.contains("--studio"), "studio flag present")
        try check(arguments.contains("--video"), "video flag present")
        try check(arguments.contains("--scale-preview"), "scale-preview flag present")
        let curatorIndex = try require(arguments.firstIndex(of: "--curator"), "--curator present")
        try check(arguments[curatorIndex + 1] == "studio", "curator value present")
    }

    private static func testRejectsDoomedRequestsBeforeProcessLaunch() throws {
        var request = RenderRequest()
        request.frames = 1
        try checkThrowsValidation(
            try ArgumentBuilder.arguments(for: request, outputDirectory: URL(fileURLWithPath: "/tmp/starforge-lab-test")),
            "argument builder validates request"
        )
    }

    private static func renderManifest(arguments: [String]) throws -> Data {
        let root = checkoutRoot()
        let output = FileManager.default.temporaryDirectory
            .appendingPathComponent("starforge-manifest-\(UUID().uuidString)", isDirectory: true)
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3", "-m", "starforge.cli", "--output", output.path] + arguments
        process.currentDirectoryURL = root
        process.environment = [
            "PATH": ProcessInfo.processInfo.environment["PATH"] ?? "/usr/bin:/bin",
            "PYTHONPATH": root.path,
            "PYTHONDONTWRITEBYTECODE": "1"
        ]

        let stderr = Pipe()
        process.standardError = stderr
        try process.run()
        process.waitUntilExit()

        if process.terminationStatus != 0 {
            let data = stderr.fileHandleForReading.readDataToEndOfFile()
            let message = String(data: data, encoding: .utf8) ?? "unknown error"
            throw CheckFailure("starforge render failed: \(message)")
        }

        defer { try? FileManager.default.removeItem(at: output) }
        return try Data(contentsOf: output.appendingPathComponent("manifest.json"))
    }

    private static func packageVersion() throws -> String {
        let root = checkoutRoot()
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3", "-c", "import starforge; print(starforge.__version__)"]
        process.currentDirectoryURL = root
        process.environment = [
            "PATH": ProcessInfo.processInfo.environment["PATH"] ?? "/usr/bin:/bin",
            "PYTHONPATH": root.path,
            "PYTHONDONTWRITEBYTECODE": "1"
        ]

        let stdout = Pipe()
        let stderr = Pipe()
        process.standardOutput = stdout
        process.standardError = stderr
        try process.run()
        process.waitUntilExit()

        if process.terminationStatus != 0 {
            let data = stderr.fileHandleForReading.readDataToEndOfFile()
            let message = String(data: data, encoding: .utf8) ?? "unknown error"
            throw CheckFailure("could not read starforge.__version__: \(message)")
        }

        let data = stdout.fileHandleForReading.readDataToEndOfFile()
        return (String(data: data, encoding: .utf8) ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func checkoutRoot() -> URL {
        var root = URL(fileURLWithPath: #filePath)
        for _ in 0..<4 {
            root.deleteLastPathComponent()
        }
        return root
    }

    private static func assertJSONRoundTrips(_ manifest: Manifest, original: Data) throws {
        let encoded = try Manifest.encode(manifest)
        let originalObject = try JSONSerialization.jsonObject(with: original) as? NSDictionary
        let encodedObject = try JSONSerialization.jsonObject(with: encoded) as? NSDictionary
        try check(originalObject == encodedObject, "manifest JSON round-trips without dropping keys")
    }

    private static func check(_ condition: Bool, _ message: String) throws {
        if !condition {
            throw CheckFailure(message)
        }
    }

    private static func checkThrowsValidation<T>(_ expression: @autoclosure () throws -> T, _ message: String) throws {
        do {
            _ = try expression()
        } catch is RenderRequest.ValidationError {
            return
        } catch {
            throw CheckFailure("\(message): wrong error \(error)")
        }
        throw CheckFailure("\(message): expected validation error")
    }

    private static func require<T>(_ value: T?, _ message: String) throws -> T {
        guard let value else {
            throw CheckFailure(message)
        }
        return value
    }
}

private struct CheckFailure: Error, CustomStringConvertible {
    let description: String

    init(_ description: String) {
        self.description = description
    }
}
