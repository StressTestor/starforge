// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "StarforgeLab",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .library(name: "StarforgeCore", targets: ["StarforgeCore"]),
        .library(name: "StarforgeEngine", targets: ["StarforgeEngine"]),
        .library(name: "StarforgePersistence", targets: ["StarforgePersistence"]),
        .executable(name: "StarforgeLab", targets: ["StarforgeLab"]),
        .executable(name: "StarforgeLabChecks", targets: ["StarforgeLabChecks"]),
        .executable(name: "StarforgeLabParity", targets: ["StarforgeLabParity"])
    ],
    targets: [
        .target(
            name: "StarforgeCore",
            path: "StarforgeLab/Packages/StarforgeCore/Sources"
        ),
        .target(
            name: "StarforgeEngine",
            dependencies: ["StarforgeCore"],
            path: "StarforgeLab/Packages/StarforgeEngine/Sources"
        ),
        .target(
            name: "StarforgePersistence",
            dependencies: ["StarforgeCore"],
            path: "StarforgeLab/Packages/StarforgePersistence/Sources"
        ),
        .executableTarget(
            name: "StarforgeLab",
            dependencies: ["StarforgeCore", "StarforgeEngine", "StarforgePersistence"],
            path: "StarforgeLab/App/Sources"
        ),
        .executableTarget(
            name: "StarforgeLabChecks",
            dependencies: ["StarforgeCore", "StarforgeEngine"],
            path: "StarforgeLab/Checks/Sources"
        ),
        .executableTarget(
            name: "StarforgeLabParity",
            dependencies: ["StarforgeCore", "StarforgeEngine"],
            path: "StarforgeLab/Parity/Sources"
        )
    ],
    swiftLanguageModes: [.v6]
)
