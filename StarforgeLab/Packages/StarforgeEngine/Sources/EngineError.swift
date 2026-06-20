import Foundation

public enum EngineError: LocalizedError, Sendable, Equatable {
    case validation(String)
    case interpreterMissing(String)
    case nonzeroExit(code: Int32, stderrTail: String)
    case manifestMissing
    case manifestDecode(String)
    case cancelled
    case assetMissing(String)

    public var errorDescription: String? {
        switch self {
        case .validation(let message):
            message
        case .interpreterMissing(let path):
            "python interpreter missing: \(path)"
        case .nonzeroExit(let code, let stderrTail):
            "starforge exited \(code): \(stderrTail)"
        case .manifestMissing:
            "starforge did not write manifest.json"
        case .manifestDecode(let message):
            "could not decode manifest.json: \(message)"
        case .cancelled:
            "render cancelled"
        case .assetMissing(let filename):
            "manifest-listed asset is missing: \(filename)"
        }
    }
}
