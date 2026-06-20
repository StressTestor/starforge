import Foundation

public struct Manifest: Codable, Sendable, Hashable {
    public let project: String
    public let version: String
    public let subject: String
    public let selectedSubject: String
    public let crossSubject: Bool
    public let seed: Int
    public let selectedSeed: Int
    public let preset: String
    public let selectedPreset: String
    public let selectedGenome: Genome
    public let width: Int
    public let height: Int
    public let frames: Int
    public let supersample: Int
    public let previewWidth: Int
    public let previewHeight: Int
    public let seedCandidates: [SeedCandidate]
    public let collection: [CollectionEntry]
    public let studio: [StudioRank]
    public let batch: Int
    public let topK: Int
    public let curator: String
    public let video: VideoStatus
    public let assets: [String]
    public let generatedAt: String
    public let python: String
    public let dependencies: Dependencies

    public static func decode(from data: Data) throws -> Manifest {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(Manifest.self, from: data)
    }

    public static func encode(_ manifest: Manifest) throws -> Data {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(manifest)
    }
}

public struct Genome: Codable, Sendable, Hashable {
    public let seed: Int
    public let preset: String
    public let subject: String
    public let centerX: Double
    public let centerY: Double
    public let diskTilt: Double
    public let diskBandCount: Int
    public let diskThickness: Double
    public let diskRadius: Double
    public let diskGap: Double
    public let diskTurbulence: Double
    public let jetAngle: Double
    public let jetWidth: Double
    public let jetLength: Double
    public let jetAsymmetry: Double
    public let horizonRadius: Double
    public let photonRadius: Double
    public let photonTightness: Double
    public let lensingStrength: Double
    public let colorTemperature: Double
    public let beamingStrength: Double
    public let rotationDirection: Int
    public let backgroundTwist: Double
}

public struct SeedCandidate: Codable, Sendable, Hashable {
    public let seed: Int
    public let score: Double?
    public let reasons: [String: Double]?

    public init(seed: Int, score: Double?, reasons: [String: Double]?) {
        self.seed = seed
        self.score = score
        self.reasons = reasons
    }

    enum CodingKeys: String, CodingKey {
        case seed
        case score
        case reasons
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        seed = try container.decode(Int.self, forKey: .seed)
        score = try container.decodeIfPresent(Double.self, forKey: .score)
        reasons = try container.decodeIfPresent([String: Double].self, forKey: .reasons)
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(seed, forKey: .seed)
        if let score {
            try container.encode(score, forKey: .score)
        } else {
            try container.encodeNil(forKey: .score)
        }
        if let reasons {
            try container.encode(reasons, forKey: .reasons)
        }
    }
}

public struct CollectionEntry: Codable, Sendable, Hashable {
    public let seed: Int
    public let preset: String
    public let score: Score
    public let genome: Genome
}

public struct Score: Codable, Sendable, Hashable {
    public let total: Double
    public let reasons: [String: Double]
}

public struct StudioRank: Codable, Sendable, Hashable {
    public let subject: String
    public let preset: String
    public let seed: Int
    public let rawTotal: Double
    public let normTotal: Double
    public let frontier: Bool
    public let subjectRank: Int
    public let why: [String]
}

public struct VideoStatus: Codable, Sendable, Hashable {
    public let mp4: String
    public let webm: String
}

public struct Dependencies: Codable, Sendable, Hashable {
    public let numpy: String
    public let pillow: String
    public let ffmpeg: String
}
