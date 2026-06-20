import Foundation
import StarforgeCore

public struct HistoryStore: Sendable {
    public let indexURL: URL

    public init(indexURL: URL) {
        self.indexURL = indexURL
    }

    public func load() throws -> [RenderRecord] {
        guard FileManager.default.fileExists(atPath: indexURL.path) else {
            return []
        }
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode([RenderRecord].self, from: Data(contentsOf: indexURL))
    }

    public func save(_ records: [RenderRecord]) throws {
        try FileManager.default.createDirectory(
            at: indexURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try encoder.encode(records).write(to: indexURL, options: [.atomic])
    }
}
