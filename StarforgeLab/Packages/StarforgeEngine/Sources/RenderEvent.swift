import Foundation
import StarforgeCore

public enum RenderEvent: Sendable, Equatable {
    case started(pid: Int32)
    case log(String)
    case manifestReady(Manifest)
    case finished(RenderRecord)
    case failed(EngineError)
}
