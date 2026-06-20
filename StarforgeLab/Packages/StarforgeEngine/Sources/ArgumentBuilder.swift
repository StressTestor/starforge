import Foundation
import StarforgeCore

public enum ArgumentBuilder {
    public static func arguments(for request: RenderRequest, outputDirectory: URL) throws -> [String] {
        let request = try request.validated()
        var arguments = [
            "-m", "starforge.cli",
            "--output", outputDirectory.path,
            "--width", "\(request.width)",
            "--height", "\(request.height)",
            "--frames", "\(request.frames)",
            "--seed", "\(request.seed)",
            "--preset", request.preset,
            "--subject", request.subject,
            "--curator", request.curator,
            "--supersample", "\(request.supersample)"
        ]

        if request.seedGallery > 0 {
            arguments += ["--seed-gallery", "\(request.seedGallery)"]
        }
        if request.batch > 0 {
            arguments += ["--batch", "\(request.batch)"]
        }
        if request.topK > 0 {
            arguments += ["--top-k", "\(request.topK)"]
        }
        if request.crossSubject {
            arguments.append("--cross-subject")
        }
        if request.studio {
            arguments.append("--studio")
        }
        if request.video {
            arguments.append("--video")
        }
        if request.scalePreview {
            arguments.append("--scale-preview")
        }
        return arguments
    }
}
