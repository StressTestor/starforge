import Foundation

public struct EngineLocations: Sendable, Equatable {
    public let executableURL: URL
    public let leadingArguments: [String]
    public let environment: [String: String]
    public let engineRoot: URL

    public init(
        executableURL: URL,
        leadingArguments: [String] = [],
        environment: [String: String],
        engineRoot: URL
    ) {
        self.executableURL = executableURL
        self.leadingArguments = leadingArguments
        self.environment = environment
        self.engineRoot = engineRoot
    }
}

public enum EngineLocator {
    public static func locate(bundle: Bundle = .main) throws -> EngineLocations {
        if let override = ProcessInfo.processInfo.environment["STARFORGE_BUNDLE_RESOURCES"], !override.isEmpty {
            return try bundledLocations(resources: URL(fileURLWithPath: override))
        }

        let resources = bundle.resourceURL
        if let resources, FileManager.default.isExecutableFile(atPath: resources.appendingPathComponent("bin/python3").path) {
            return try bundledLocations(resources: resources)
        }

        let devRoot = developmentRoot(bundle: bundle)
        guard FileManager.default.fileExists(atPath: devRoot.appendingPathComponent("starforge/cli.py").path) else {
            throw EngineError.interpreterMissing("bundled Python.xcframework or development checkout")
        }

        var environment = baseEnvironment()
        environment["PYTHONPATH"] = devRoot.path
        return EngineLocations(
            executableURL: URL(fileURLWithPath: "/usr/bin/env"),
            leadingArguments: ["python3"],
            environment: environment,
            engineRoot: devRoot
        )
    }

    private static func baseEnvironment() -> [String: String] {
        var environment = ProcessInfo.processInfo.environment
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONHASHSEED"] = "0"
        environment["PATH"] = environment["PATH"] ?? "/usr/bin:/bin:/opt/homebrew/bin"
        return environment
    }

    private static func bundledLocations(resources: URL) throws -> EngineLocations {
        let python = resources.appendingPathComponent("bin/python3")
        let engine = resources.appendingPathComponent("engine")
        let pysite = resources.appendingPathComponent("pysite")
        let pythonHome = resources.appendingPathComponent("Python.xcframework/macos-arm64_x86_64/Python.framework/Versions/3.12")

        guard FileManager.default.isExecutableFile(atPath: python.path) else {
            throw EngineError.interpreterMissing(python.path)
        }
        guard FileManager.default.fileExists(atPath: engine.appendingPathComponent("starforge/cli.py").path) else {
            throw EngineError.interpreterMissing(engine.path)
        }

        var environment = baseEnvironment()
        environment["PYTHONPATH"] = pythonPath([engine, pysite])
        environment["PYTHONHOME"] = pythonHome.path
        return EngineLocations(
            executableURL: python,
            environment: environment,
            engineRoot: engine
        )
    }

    private static func pythonPath(_ urls: [URL]) -> String {
        urls.map(\.path).joined(separator: ":")
    }

    private static func developmentRoot(bundle: Bundle) -> URL {
        if let override = ProcessInfo.processInfo.environment["STARFORGE_ENGINE_ROOT"], !override.isEmpty {
            return URL(fileURLWithPath: override)
        }

        var candidate = bundle.bundleURL
        for _ in 0..<4 {
            candidate.deleteLastPathComponent()
            if FileManager.default.fileExists(atPath: candidate.appendingPathComponent("starforge/cli.py").path) {
                return candidate
            }
        }

        return URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
    }

}
