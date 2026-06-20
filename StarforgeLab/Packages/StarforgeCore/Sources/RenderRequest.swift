import Foundation

public enum Preset: String, CaseIterable, Sendable {
    case eventHorizon = "event-horizon"
    case neonCollapse = "neon-collapse"
    case coldSingularity = "cold-singularity"
    case solarWound = "solar-wound"
    case deepField = "deep-field"

    public static let allNames = allCases.map(\.rawValue)
}

public enum Subject: String, CaseIterable, Sendable {
    case blackHole = "black-hole"
    case lensedGalaxy = "lensed-galaxy"
    case neutronStar = "neutron-star"
    case wormhole

    public static let allNames = allCases.map(\.rawValue)
}

public enum Curator: String, CaseIterable, Sendable {
    case heuristic
    case studio

    public static let allNames = allCases.map(\.rawValue)
}

public struct RenderRequest: Codable, Sendable, Hashable {
    public var width: Int
    public var height: Int
    public var frames: Int
    public var seed: Int
    public var preset: String
    public var subject: String
    public var supersample: Int
    public var seedGallery: Int
    public var batch: Int
    public var topK: Int
    public var crossSubject: Bool
    public var studio: Bool
    public var video: Bool
    public var scalePreview: Bool
    public var curator: String

    public init(
        width: Int = 1600,
        height: Int = 2200,
        frames: Int = 42,
        seed: Int = 260613,
        preset: String = "neon-collapse",
        subject: String = "black-hole",
        supersample: Int = 1,
        seedGallery: Int = 0,
        batch: Int = 0,
        topK: Int = 0,
        crossSubject: Bool = false,
        studio: Bool = false,
        video: Bool = false,
        scalePreview: Bool = false,
        curator: String = "heuristic"
    ) {
        self.width = width
        self.height = height
        self.frames = frames
        self.seed = seed
        self.preset = preset
        self.subject = subject
        self.supersample = supersample
        self.seedGallery = seedGallery
        self.batch = batch
        self.topK = topK
        self.crossSubject = crossSubject
        self.studio = studio
        self.video = video
        self.scalePreview = scalePreview
        self.curator = curator
    }

    public func validated() throws -> RenderRequest {
        try Self.require((64...5000).contains(width), "width must be 64...5000")
        try Self.require((64...5000).contains(height), "height must be 64...5000")
        try Self.require((2...180).contains(frames), "frames must be 2...180")
        try Self.require((1...3).contains(supersample), "supersample must be 1...3")
        try Self.require(seedGallery >= 0, "seed gallery count cannot be negative")
        try Self.require(batch >= 0, "batch count cannot be negative")
        try Self.require(topK >= 0, "top-k cannot be negative")
        try Self.require(Preset.allNames.contains(preset), "unknown preset: \(preset)")
        try Self.require(Subject.allNames.contains(subject), "unknown subject: \(subject)")
        try Self.require(Curator.allNames.contains(curator), "unknown curator: \(curator)")
        return self
    }

    private static func require(_ condition: Bool, _ message: String) throws {
        if !condition {
            throw ValidationError(message)
        }
    }

    public struct ValidationError: LocalizedError, Equatable, Sendable {
        public let message: String

        public init(_ message: String) {
            self.message = message
        }

        public var errorDescription: String? { message }
    }
}

public struct RenderRecord: Codable, Sendable, Hashable, Identifiable {
    public let id: UUID
    public let request: RenderRequest
    public let manifest: Manifest
    public let outputDirectory: String
    public let createdAt: Date

    public init(
        id: UUID = UUID(),
        request: RenderRequest,
        manifest: Manifest,
        outputDirectory: String,
        createdAt: Date = Date()
    ) {
        self.id = id
        self.request = request
        self.manifest = manifest
        self.outputDirectory = outputDirectory
        self.createdAt = createdAt
    }
}
