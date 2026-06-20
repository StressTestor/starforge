import Foundation
import StarforgeCore

public actor RenderService {
    public init() {}

    public func run(_ request: RenderRequest, into directory: URL) -> AsyncThrowingStream<RenderEvent, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    try await execute(request, into: directory, continuation: continuation)
                    continuation.finish()
                } catch let error as EngineError {
                    continuation.yield(.failed(error))
                    continuation.finish(throwing: error)
                } catch {
                    continuation.yield(.failed(.manifestDecode(error.localizedDescription)))
                    continuation.finish(throwing: error)
                }
            }

            continuation.onTermination = { _ in
                task.cancel()
            }
        }
    }

    private func execute(
        _ request: RenderRequest,
        into directory: URL,
        continuation: AsyncThrowingStream<RenderEvent, Error>.Continuation
    ) async throws {
        _ = try request.validated()
        if Task.isCancelled {
            throw EngineError.cancelled
        }

        try prepareOutputDirectory(directory)
        let locations = try EngineLocator.locate()
        let arguments = try ArgumentBuilder.arguments(for: request, outputDirectory: directory)
        let result = try ProcessRunner.run(
            executableURL: locations.executableURL,
            arguments: locations.leadingArguments + arguments,
            environment: locations.environment,
            currentDirectory: locations.engineRoot
        ) { pid in
            continuation.yield(.started(pid: pid))
        }

        for line in result.stdoutLines + result.stderrLines {
            continuation.yield(.log(line))
        }

        if Task.isCancelled {
            try? FileManager.default.removeItem(at: directory)
            throw EngineError.cancelled
        }

        guard result.exitCode == 0 else {
            throw EngineError.nonzeroExit(code: result.exitCode, stderrTail: result.stderrLines.suffix(8).joined(separator: "\n"))
        }

        let manifestURL = directory.appendingPathComponent("manifest.json")
        guard FileManager.default.fileExists(atPath: manifestURL.path) else {
            throw EngineError.manifestMissing
        }

        let manifest: Manifest
        do {
            manifest = try Manifest.decode(from: Data(contentsOf: manifestURL))
        } catch {
            throw EngineError.manifestDecode(error.localizedDescription)
        }
        continuation.yield(.manifestReady(manifest))

        for asset in manifest.assets {
            let assetURL = directory.appendingPathComponent(asset)
            if !FileManager.default.fileExists(atPath: assetURL.path) {
                throw EngineError.assetMissing(asset)
            }
        }

        let record = RenderRecord(request: request, manifest: manifest, outputDirectory: directory.path)
        continuation.yield(.finished(record))
    }

    private func prepareOutputDirectory(_ directory: URL) throws {
        let fileManager = FileManager.default
        if fileManager.fileExists(atPath: directory.path) {
            try fileManager.removeItem(at: directory)
        }
        try fileManager.createDirectory(at: directory, withIntermediateDirectories: true)
    }
}

public struct ProcessResult: Sendable, Equatable {
    public let exitCode: Int32
    public let stdoutLines: [String]
    public let stderrLines: [String]
}

enum ProcessRunner {
    static func run(
        executableURL: URL,
        arguments: [String],
        environment: [String: String],
        currentDirectory: URL,
        onStart: (Int32) -> Void
    ) throws -> ProcessResult {
        let process = Process()
        process.executableURL = executableURL
        process.arguments = arguments
        process.environment = environment
        process.currentDirectoryURL = currentDirectory

        let stdout = Pipe()
        let stderr = Pipe()
        process.standardOutput = stdout
        process.standardError = stderr

        try process.run()
        onStart(process.processIdentifier)
        process.waitUntilExit()

        let stdoutText = String(data: stdout.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        let stderrText = String(data: stderr.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        return ProcessResult(
            exitCode: process.terminationStatus,
            stdoutLines: stdoutText.split(whereSeparator: \.isNewline).map(String.init),
            stderrLines: stderrText.split(whereSeparator: \.isNewline).map(String.init)
        )
    }
}
