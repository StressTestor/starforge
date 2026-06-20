import Foundation

public enum OutputLayout {
    public static func defaultLibraryRoot() throws -> URL {
        let base = try FileManager.default.url(
            for: .applicationSupportDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )
        let root = base.appendingPathComponent("StarforgeLab/Renders", isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        return root
    }

    public static func freshRenderDirectory(in root: URL) -> URL {
        root.appendingPathComponent(UUID().uuidString, isDirectory: true)
    }
}
